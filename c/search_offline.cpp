///////////////////////////////////////////////////////////////////////////////////////////////
// Homemade GPS Receiver
// Copyright (c) Andrew Holme 2011-2013
// http://www.holmea.demon.co.uk/GPS/Main.htm
///////////////////////////////////////////////////////////////////////////////////////////////

#include <memory.h>
#include <fftw3.h>
#include <math.h>

#include "gps_offline.h"
#include "cacode.h"

///////////////////////////////////////////////////////////////////////////////////////////////

struct SATELLITE {
    int prn, navstar, T1, T2;
};

static const SATELLITE Sats[NUM_SATS] = {
     {1,  63,  2,  6},
     {2,  56,  3,  7},
     {3,  37,  4,  8},
     {4,  35,  5,  9},
     {5,  64,  1,  9},
     {6,  36,  2, 10},
     {7,  62,  1,  8},
     {8,  44,  2,  9},
     {9,  33,  3, 10},
    {10,  38,  2,  3},
    {11,  46,  3,  4},
    {12,  59,  5,  6},
    {13,  43,  6,  7},
    {14,  49,  7,  8},
    {15,  60,  8,  9},
    {16,  51,  9, 10},
    {17,  57,  1,  4},
    {18,  50,  2,  5},
    {19,  54,  3,  6},
    {20,  47,  4,  7},
    {21,  52,  5,  8},
    {22,  53,  6,  9},
    {23,  55,  1,  3},
    {24,  23,  4,  6},
    {25,  24,  5,  7},
    {26,  26,  6,  8},
    {27,  27,  7,  9},
    {28,  48,  8, 10},
    {29,  61,  1,  6},
    {30,  39,  2,  7},
    {31,  58,  3,  8},
    {32,  22,  4,  9},
};

static bool Busy[NUM_SATS];

///////////////////////////////////////////////////////////////////////////////////////////////

static fftwf_complex code[NUM_SATS][FFT_LEN];

static fftwf_complex fwd_buf[FFT_LEN],
                     rev_buf[FFT_LEN];

static fftwf_plan fwd_plan, rev_plan;

///////////////////////////////////////////////////////////////////////////////////////////////

float inline Bipolar(int bit) {
    return bit? -1.0 : +1.0;
}

///////////////////////////////////////////////////////////////////////////////////////////////

int SearchInit() {

    const float ca_rate = CPS/FS;

    fwd_plan = fftwf_plan_dft_1d(FFT_LEN, fwd_buf, fwd_buf, FFTW_FORWARD,  FFTW_ESTIMATE);
    rev_plan = fftwf_plan_dft_1d(FFT_LEN, rev_buf, rev_buf, FFTW_BACKWARD, FFTW_ESTIMATE);

    for (int sv=0; sv<NUM_SATS; sv++) {

        CACODE ca(Sats[sv].T1, Sats[sv].T2);
        float ca_phase=0;

        for (int i=0; i<FFT_LEN; i++) {

            float chip = Bipolar(ca.Chip()); // chip at start of sample period

            ca_phase += ca_rate; // NCO phase at end of period

            if (ca_phase >= 1.0) { // reached or crossed chip boundary?
                ca_phase -= 1.0;
                ca.Clock();

                // These two lines do not make much difference
                chip *= 1.0 - ca_phase;                 // prev chip
                chip += ca_phase * Bipolar(ca.Chip());  // next chip
            }

            fwd_buf[i][0] = chip;
            fwd_buf[i][1] = 0;
        }

        fftwf_execute(fwd_plan);
        memcpy(code[sv], fwd_buf, sizeof fwd_buf);
    }

    return 0;
}

///////////////////////////////////////////////////////////////////////////////////////////////

void SearchFree() {
    fftwf_destroy_plan(fwd_plan);
    fftwf_destroy_plan(rev_plan);
}

///////////////////////////////////////////////////////////////////////////////////////////////

static int Sample(FILE *fp) {
//    const int lo_sin[] = {1,1,0,0}; // Quadrature local oscillators
//    const int lo_cos[] = {1,0,0,1};
    const int lo_sin[] = {1,1,0,0}; // Quadrature local oscillators
    const int lo_cos[] = {0,1,1,0};

    const float lo_rate = 4*FC/FS; // NCO rate

    const int PACKET = 512;

    float lo_phase=0; // NCO phase accumulator
    int i=0, j, k, byte, bit, read_count;

    unsigned char rx[PACKET];
    while (i<FFT_LEN) {
        read_count = fread(rx, 1, PACKET, fp);
        if (read_count != PACKET) {
//          printf("read error!\n");
          return(1);
        }
        for (j=0; j<PACKET; j++) {

            byte = rx[j];
            for (k=i+8; i<k; i++) {
                bit = byte&1;
                byte>>=1;

                // Down convert to complex (IQ) baseband by mixing (XORing)
                // samples with quadrature local oscillators
//                fwd_buf[i][0] = Bipolar(bit ^ lo_sin[int(lo_phase)]);
//                fwd_buf[i][1] = Bipolar(bit ^ lo_cos[int(lo_phase)]);
                fwd_buf[i][0] = Bipolar(bit ^ lo_cos[int(lo_phase)]);
                fwd_buf[i][1] = Bipolar(bit ^ lo_sin[int(lo_phase)]);

                lo_phase += lo_rate;
                if (lo_phase>=4) lo_phase-=4;
            }
        }
    }

    fftwf_execute(fwd_plan); // Transform to frequency domain

    return(0);
//    NextTask();
}

///////////////////////////////////////////////////////////////////////////////////////////////

static float Correlate(int sv, int *max_snr_dop, int *max_snr_i) {

    fftwf_complex *data = fwd_buf;
    fftwf_complex *prod = rev_buf;
    float max_snr=0;
    int i;

    for (int dop=( -max_fo*(double)FFT_LEN/(double)FS ); dop<= ( max_fo*(double)FFT_LEN/(double)FS  ); dop++) {
        float max_pwr=0, tot_pwr=0;
        int max_pwr_i;

        // (a-ib)(x+iy) = (ax+by) + i(ay-bx)
        for (i=0; i<FFT_LEN; i++) {
            int j=(i-dop+FFT_LEN)%FFT_LEN;
            prod[i][0] = data[i][0]*code[sv][j][0] + data[i][1]*code[sv][j][1];
            prod[i][1] = data[i][0]*code[sv][j][1] - data[i][1]*code[sv][j][0];
        }

        fftwf_execute(rev_plan);
//        NextTask();

        for (i=0; i<FS/1000; i++) {
            float pwr = prod[i][0]*prod[i][0] + prod[i][1]*prod[i][1];
            if (pwr>max_pwr) max_pwr=pwr, max_pwr_i=i;
            tot_pwr += pwr;
        }

        float ave_pwr = tot_pwr/i;
        float snr = max_pwr/ave_pwr;
        if (snr>max_snr) max_snr=snr, *max_snr_dop=dop, *max_snr_i=max_pwr_i;
    }
    return max_snr;
}

///////////////////////////////////////////////////////////////////////////////////////////////

int SearchCode(int sv, int g1) { // Could do this with look-up tables
    int chips=0;
    for (CACODE ca(Sats[sv].T1, Sats[sv].T2); ca.GetG1()!=(unsigned int)g1; ca.Clock()) chips++;
    return chips;
}

///////////////////////////////////////////////////////////////////////////////////////////////

void SearchEnable(int sv) {
    Busy[sv] = false;
}

///////////////////////////////////////////////////////////////////////////////////////////////

void SearchTask(char *filename_1bit_bin) {
    int sv, lo_shift, ca_shift;
    float snr;
    FILE *fp;

    fp = fopen(filename_1bit_bin, "rb");
    if (fp == NULL) {
      printf("can not open file!\n");
      return;
    }
    int run_out = 0;
    int run_count = 0;
    float sat_snr_store[NUM_SATS];
    float snr_store[NUM_SATS];
    int   sv_store[NUM_SATS];
    int   lo_store[NUM_SATS];
    int   ca_store[NUM_SATS];
    int hit_count, i;
    for(;;) {
        hit_count = 0;
        for (sv=0; sv<NUM_SATS; sv++) {
            run_out = Sample(fp);
            if (run_out) {
              printf("run out of file!\n");
              break;
            }

            snr = Correlate(sv, &lo_shift, &ca_shift);
            sat_snr_store[sv] = snr;
            if (snr<25) {
                continue;
            }
            else {
              snr_store[hit_count] = snr;
              sv_store[hit_count] = sv;
              lo_store[hit_count] = lo_shift;
              ca_store[hit_count] = ca_shift;
              hit_count++;
            }
        }

        if (run_out) {
          break;
        }

        printf("%2d satellite: ", run_count);
        for (i=0; i<hit_count; i++) {
          printf("%5d ", sv_store[i]);
        }
        printf("\n");
        printf("%2d SNR(>=25): ", run_count);
        for (i=0; i<hit_count; i++) {
          printf("%5.1f ", snr_store[i]);
        }
        printf("\n");
        printf("%2d  lo_shift: ", run_count);
        for (i=0; i<hit_count; i++) {
          printf("%5d ", lo_store[i]);
        }
        printf("\n");
        printf("%2d  ca_shift: ", run_count);
        for (i=0; i<hit_count; i++) {
          printf("%5d ", ca_store[i]);
        }
        printf("\n");
        for (sv=0; sv<NUM_SATS; sv++) {
          printf("%2.0f ", sat_snr_store[sv]);
        }
        printf("\n\n");
        run_count++;

    }
    fclose(fp);
}
