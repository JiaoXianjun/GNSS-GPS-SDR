///////////////////////////////////////////////////////////////////////////////////////////////
// Homemade GPS Receiver
// Copyright (c) Andrew Holme 2011-2013
// http://www.holmea.demon.co.uk/GPS/Main.htm
///////////////////////////////////////////////////////////////////////////////////////////////

#include <memory.h>
#include <stdio.h>
#include <math.h>

#include "gps.h"
#include "ephemeris.h"
#include "spi.h"

#define MAX_ITER 20

#define WGS84_A     (6378137.0)
#define WGS84_F_INV (298.257223563)
#define WGS84_B     (6356752.31424518)
#define WGS84_E2    (0.00669437999014132)

///////////////////////////////////////////////////////////////////////////////////////////////

struct SNAPSHOT {
    EPHEM eph;
    float power;
    int ch, sv, ms, bits, g1, ca_phase;
    bool LoadAtomic(int ch, uint16_t *up, uint16_t *dn);
    double GetClock();
};

static SNAPSHOT Replicas[NUM_CHANS];

///////////////////////////////////////////////////////////////////////////////////////////////
// Gather channel data and consistent ephemerides

bool SNAPSHOT::LoadAtomic(int ch, uint16_t *up, uint16_t *dn) {

    /* Called inside atomic section - yielding not allowed */

    if (ChanSnapshot(
        ch,     // in: channel id
        up[1],  // in: FPGA circular buffer pointer
        &sv,    // out: satellite id
        &bits,  // out: total bits held locally (CHANNEL struct) + remotely (FPGA)
        &power) // out: received signal strength ^ 2
    && Ephemeris[sv].Valid()) {

        ms = up[0];
        g1 = dn[0] & 0x3FF;
        ca_phase = dn[0] >> 10;

        memcpy(&eph, Ephemeris+sv, sizeof eph);
        return true;
    }
    else
        return false; // channel not ready
}

///////////////////////////////////////////////////////////////////////////////////////////////

static int LoadAtomic() {
    const int WPC=3;

    SPI_MISO clocks;
    int chans=0;

    // Yielding to other tasks not allowed after spi_hog returns
    spi_hog(CmdGetClocks, &clocks, 2+NUM_CHANS*WPC*2);

    uint16_t srq = clocks.word[0];              // un-serviced epochs
    uint16_t *up = clocks.word+1;               // Embedded CPU memory
    uint16_t *dn = clocks.word+WPC*NUM_CHANS;   // FPGA clocks (in reverse order)

    for (int ch=0; ch<NUM_CHANS; ch++, srq>>=1, up+=WPC, dn-=WPC) {

        up[0] += (srq&1); // add 1ms for un-serviced epochs

        if (Replicas[chans].LoadAtomic(ch,up,dn))
            Replicas[chans++].ch=ch;
    }

    // Safe to yield again ...
    return chans;
}

///////////////////////////////////////////////////////////////////////////////////////////////

static int LoadReplicas() {
    const int GLITCH_GUARD=500;
    SPI_MISO glitches[2];

    // Get glitch counters "before"
    spi_get(CmdGetGlitches, glitches+0, NUM_CHANS*2);
    TimerWait(GLITCH_GUARD);

    // Gather consistent snapshot of all channels
    int pass1 = LoadAtomic();
    int pass2 = 0;

    // Get glitch counters "after"
    TimerWait(GLITCH_GUARD);
    spi_get(CmdGetGlitches, glitches+1, NUM_CHANS*2);

    // Strip noisy channels
    for (int i=0; i<pass1; i++) {
        int ch = Replicas[i].ch;
        if (glitches[0].word[ch]!=glitches[1].word[ch]) continue;
        if (i>pass2) memcpy(Replicas+pass2, Replicas+i, sizeof(SNAPSHOT));
        pass2++;
    }

    return pass2;
}

///////////////////////////////////////////////////////////////////////////////////////////////

double SNAPSHOT::GetClock() {

    // Find 10-bit shift register in 1023 state sequence
    int chips = SearchCode(sv, g1);

    // TOW refers to leading edge of next (un-processed) subframe.
    // Channel.cpp processes NAV data up to the subframe boundary.
    // Un-processed bits remain in holding buffers.

    return // Un-corrected satellite clock
        eph.tow * 6 +                   // Time of week in seconds
        bits / BPS  +                   // NAV data bits buffered
        ms * 1e-3   +                   // Milliseconds since last bit (0...20)
        chips / CPS +                   // Code chips (0...1022)
        ca_phase * pow(2, -6) / CPS;    // Code NCO phase
}

///////////////////////////////////////////////////////////////////////////////////////////////

static int Solve(int chans, double *x_n, double *y_n, double *z_n, double *t_bias) {
    int sv, i, j, r, c;

    double t_tx[NUM_CHANS]; // Clock replicas in seconds since start of week

    double x_sv[NUM_CHANS],
           y_sv[NUM_CHANS],
           z_sv[NUM_CHANS];

    double t_pc;  // Uncorrected system time when clock replica snapshots taken
    double t_rx;    // Corrected GPS time

    double dPR[NUM_CHANS]; // Pseudo range error

    double jac[NUM_CHANS][4], ma[4][4], mb[4][4], mc[4][NUM_CHANS], md[4];

    double weight[NUM_CHANS];

    *x_n = *y_n = *z_n = *t_bias = t_pc = 0;

    for (i=0; i<chans; i++) {
        NextTask();

        weight[i] = Replicas[i].power;

        // Un-corrected time of transmission
        t_tx[i] = Replicas[i].GetClock();

        // Clock correction
        t_tx[i] -= Replicas[i].eph.GetClockCorrection(t_tx[i]);

        // Get SV position in ECEF coords
        Replicas[i].eph.GetXYZ(x_sv+i, y_sv+i, z_sv+i, t_tx[i]);

        t_pc += t_tx[i];
    }

    // Approximate starting value for receiver clock
    t_pc = t_pc/chans + 75e-3;

    // Iterate to user xyzt solution using Taylor Series expansion:
    for(j=0; j<MAX_ITER; j++) {
        NextTask();

        t_rx = t_pc - *t_bias;

        for (i=0; i<chans; i++) {
            // Convert SV position to ECI coords (20.3.3.4.3.3.2)
            double theta = (t_tx[i] - t_rx) * OMEGA_E;

            double x_sv_eci = x_sv[i]*cos(theta) - y_sv[i]*sin(theta);
            double y_sv_eci = x_sv[i]*sin(theta) + y_sv[i]*cos(theta);
            double z_sv_eci = z_sv[i];

            // Geometric range (20.3.3.4.3.4)
            double gr = sqrt(pow(*x_n - x_sv_eci, 2) +
                             pow(*y_n - y_sv_eci, 2) +
                             pow(*z_n - z_sv_eci, 2));

            dPR[i] = C*(t_rx - t_tx[i]) - gr;

            jac[i][0] = (*x_n - x_sv_eci) / gr;
            jac[i][1] = (*y_n - y_sv_eci) / gr;
            jac[i][2] = (*z_n - z_sv_eci) / gr;
            jac[i][3] = C;
        }

        // ma = transpose(H) * W * H
        for (r=0; r<4; r++)
            for (c=0; c<4; c++) {
            ma[r][c] = 0;
            for (i=0; i<chans; i++) ma[r][c] += jac[i][r]*weight[i]*jac[i][c];
        }

        double determinant =
            ma[0][3]*ma[1][2]*ma[2][1]*ma[3][0] - ma[0][2]*ma[1][3]*ma[2][1]*ma[3][0] - ma[0][3]*ma[1][1]*ma[2][2]*ma[3][0] + ma[0][1]*ma[1][3]*ma[2][2]*ma[3][0]+
            ma[0][2]*ma[1][1]*ma[2][3]*ma[3][0] - ma[0][1]*ma[1][2]*ma[2][3]*ma[3][0] - ma[0][3]*ma[1][2]*ma[2][0]*ma[3][1] + ma[0][2]*ma[1][3]*ma[2][0]*ma[3][1]+
            ma[0][3]*ma[1][0]*ma[2][2]*ma[3][1] - ma[0][0]*ma[1][3]*ma[2][2]*ma[3][1] - ma[0][2]*ma[1][0]*ma[2][3]*ma[3][1] + ma[0][0]*ma[1][2]*ma[2][3]*ma[3][1]+
            ma[0][3]*ma[1][1]*ma[2][0]*ma[3][2] - ma[0][1]*ma[1][3]*ma[2][0]*ma[3][2] - ma[0][3]*ma[1][0]*ma[2][1]*ma[3][2] + ma[0][0]*ma[1][3]*ma[2][1]*ma[3][2]+
            ma[0][1]*ma[1][0]*ma[2][3]*ma[3][2] - ma[0][0]*ma[1][1]*ma[2][3]*ma[3][2] - ma[0][2]*ma[1][1]*ma[2][0]*ma[3][3] + ma[0][1]*ma[1][2]*ma[2][0]*ma[3][3]+
            ma[0][2]*ma[1][0]*ma[2][1]*ma[3][3] - ma[0][0]*ma[1][2]*ma[2][1]*ma[3][3] - ma[0][1]*ma[1][0]*ma[2][2]*ma[3][3] + ma[0][0]*ma[1][1]*ma[2][2]*ma[3][3];

        // mb = inverse(ma) = inverse(transpose(H)*W*H)
        mb[0][0] = (ma[1][2]*ma[2][3]*ma[3][1] - ma[1][3]*ma[2][2]*ma[3][1] + ma[1][3]*ma[2][1]*ma[3][2] - ma[1][1]*ma[2][3]*ma[3][2] - ma[1][2]*ma[2][1]*ma[3][3] + ma[1][1]*ma[2][2]*ma[3][3]) / determinant;
        mb[0][1] = (ma[0][3]*ma[2][2]*ma[3][1] - ma[0][2]*ma[2][3]*ma[3][1] - ma[0][3]*ma[2][1]*ma[3][2] + ma[0][1]*ma[2][3]*ma[3][2] + ma[0][2]*ma[2][1]*ma[3][3] - ma[0][1]*ma[2][2]*ma[3][3]) / determinant;
        mb[0][2] = (ma[0][2]*ma[1][3]*ma[3][1] - ma[0][3]*ma[1][2]*ma[3][1] + ma[0][3]*ma[1][1]*ma[3][2] - ma[0][1]*ma[1][3]*ma[3][2] - ma[0][2]*ma[1][1]*ma[3][3] + ma[0][1]*ma[1][2]*ma[3][3]) / determinant;
        mb[0][3] = (ma[0][3]*ma[1][2]*ma[2][1] - ma[0][2]*ma[1][3]*ma[2][1] - ma[0][3]*ma[1][1]*ma[2][2] + ma[0][1]*ma[1][3]*ma[2][2] + ma[0][2]*ma[1][1]*ma[2][3] - ma[0][1]*ma[1][2]*ma[2][3]) / determinant;
        mb[1][0] = (ma[1][3]*ma[2][2]*ma[3][0] - ma[1][2]*ma[2][3]*ma[3][0] - ma[1][3]*ma[2][0]*ma[3][2] + ma[1][0]*ma[2][3]*ma[3][2] + ma[1][2]*ma[2][0]*ma[3][3] - ma[1][0]*ma[2][2]*ma[3][3]) / determinant;
        mb[1][1] = (ma[0][2]*ma[2][3]*ma[3][0] - ma[0][3]*ma[2][2]*ma[3][0] + ma[0][3]*ma[2][0]*ma[3][2] - ma[0][0]*ma[2][3]*ma[3][2] - ma[0][2]*ma[2][0]*ma[3][3] + ma[0][0]*ma[2][2]*ma[3][3]) / determinant;
        mb[1][2] = (ma[0][3]*ma[1][2]*ma[3][0] - ma[0][2]*ma[1][3]*ma[3][0] - ma[0][3]*ma[1][0]*ma[3][2] + ma[0][0]*ma[1][3]*ma[3][2] + ma[0][2]*ma[1][0]*ma[3][3] - ma[0][0]*ma[1][2]*ma[3][3]) / determinant;
        mb[1][3] = (ma[0][2]*ma[1][3]*ma[2][0] - ma[0][3]*ma[1][2]*ma[2][0] + ma[0][3]*ma[1][0]*ma[2][2] - ma[0][0]*ma[1][3]*ma[2][2] - ma[0][2]*ma[1][0]*ma[2][3] + ma[0][0]*ma[1][2]*ma[2][3]) / determinant;
        mb[2][0] = (ma[1][1]*ma[2][3]*ma[3][0] - ma[1][3]*ma[2][1]*ma[3][0] + ma[1][3]*ma[2][0]*ma[3][1] - ma[1][0]*ma[2][3]*ma[3][1] - ma[1][1]*ma[2][0]*ma[3][3] + ma[1][0]*ma[2][1]*ma[3][3]) / determinant;
        mb[2][1] = (ma[0][3]*ma[2][1]*ma[3][0] - ma[0][1]*ma[2][3]*ma[3][0] - ma[0][3]*ma[2][0]*ma[3][1] + ma[0][0]*ma[2][3]*ma[3][1] + ma[0][1]*ma[2][0]*ma[3][3] - ma[0][0]*ma[2][1]*ma[3][3]) / determinant;
        mb[2][2] = (ma[0][1]*ma[1][3]*ma[3][0] - ma[0][3]*ma[1][1]*ma[3][0] + ma[0][3]*ma[1][0]*ma[3][1] - ma[0][0]*ma[1][3]*ma[3][1] - ma[0][1]*ma[1][0]*ma[3][3] + ma[0][0]*ma[1][1]*ma[3][3]) / determinant;
        mb[2][3] = (ma[0][3]*ma[1][1]*ma[2][0] - ma[0][1]*ma[1][3]*ma[2][0] - ma[0][3]*ma[1][0]*ma[2][1] + ma[0][0]*ma[1][3]*ma[2][1] + ma[0][1]*ma[1][0]*ma[2][3] - ma[0][0]*ma[1][1]*ma[2][3]) / determinant;
        mb[3][0] = (ma[1][2]*ma[2][1]*ma[3][0] - ma[1][1]*ma[2][2]*ma[3][0] - ma[1][2]*ma[2][0]*ma[3][1] + ma[1][0]*ma[2][2]*ma[3][1] + ma[1][1]*ma[2][0]*ma[3][2] - ma[1][0]*ma[2][1]*ma[3][2]) / determinant;
        mb[3][1] = (ma[0][1]*ma[2][2]*ma[3][0] - ma[0][2]*ma[2][1]*ma[3][0] + ma[0][2]*ma[2][0]*ma[3][1] - ma[0][0]*ma[2][2]*ma[3][1] - ma[0][1]*ma[2][0]*ma[3][2] + ma[0][0]*ma[2][1]*ma[3][2]) / determinant;
        mb[3][2] = (ma[0][2]*ma[1][1]*ma[3][0] - ma[0][1]*ma[1][2]*ma[3][0] - ma[0][2]*ma[1][0]*ma[3][1] + ma[0][0]*ma[1][2]*ma[3][1] + ma[0][1]*ma[1][0]*ma[3][2] - ma[0][0]*ma[1][1]*ma[3][2]) / determinant;
        mb[3][3] = (ma[0][1]*ma[1][2]*ma[2][0] - ma[0][2]*ma[1][1]*ma[2][0] + ma[0][2]*ma[1][0]*ma[2][1] - ma[0][0]*ma[1][2]*ma[2][1] - ma[0][1]*ma[1][0]*ma[2][2] + ma[0][0]*ma[1][1]*ma[2][2]) / determinant;

        // mc = inverse(transpose(H)*W*H) * transpose(H)
        for (r=0; r<4; r++)
            for (c=0; c<chans; c++) {
            mc[r][c] = 0;
            for (i=0; i<4; i++) mc[r][c] += mb[r][i]*jac[c][i];
        }

        // md = inverse(transpose(H)*W*H) * transpose(H) * W * dPR
        for (r=0; r<4; r++) {
            md[r] = 0;
            for (i=0; i<chans; i++) md[r] += mc[r][i]*weight[i]*dPR[i];
        }

        double dx = md[0];
        double dy = md[1];
        double dz = md[2];
        double dt = md[3];

        double err_mag = sqrt(dx*dx + dy*dy + dz*dz);

        // printf("%14g%14g%14g%14g%14g\n", err_mag, t_bias, x_n, y_n, z_n);

        if (err_mag<1.0) break;

        *x_n    += dx;
        *y_n    += dy;
        *z_n    += dz;
        *t_bias += dt;
    }

//    UserStat(STAT_TIME, t_rx);
    return j;
}

///////////////////////////////////////////////////////////////////////////////////////////////

static void LatLonAlt(
    double x_n, double y_n, double z_n,
    double& lat, double& lon, double& alt) {

    const double a  = WGS84_A;
    const double e2 = WGS84_E2;

    const double p = sqrt(x_n*x_n + y_n*y_n);

    lon = 2.0 * atan2(y_n, x_n + p);
    lat = atan(z_n / (p * (1.0 - e2)));
    alt = 0.0;

    for (;;) {
        double tmp = alt;
        double N = a / sqrt(1.0 - e2*pow(sin(lat),2));
        alt = p/cos(lat) - N;
        lat = atan(z_n / (p * (1.0 - e2*N/(N + alt))));
        if (fabs(alt-tmp)<1e-3) break;
    }
}

///////////////////////////////////////////////////////////////////////////////////////////////

void SolveTask() {
    double x, y, z, t_b, lat, lon, alt;
    for (;;) {
        TimerWait(4000);
        int chans = LoadReplicas();
        if (chans<4) continue;
        int iter = Solve(chans, &x, &y, &z, &t_b);
        if (iter==MAX_ITER) continue;
        LatLonAlt(x, y, z, lat, lon, alt);
//        UserStat(STAT_LAT, lat*180/PI);
//        UserStat(STAT_LON, lon*180/PI);
//        UserStat(STAT_ALT, alt, chans);
        printf(
            "\n%d,%3d,%10.6f,"
//          "%10.0f,%10.0f,%10.0f,"
            "%10.5f,%10.5f,%8.2f\n\n",
            chans, iter, t_b,
//          x, y, z,
            lat*180/PI, lon*180/PI, alt);
    }
}
