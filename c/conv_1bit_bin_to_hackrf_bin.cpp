///////////////////////////////////////////////////////////////////////////////////////////////
// Homemade GPS Receiver
// Copyright (c) Andrew Holme 2011-2013
// http://www.holmea.demon.co.uk/GPS/Main.htm
///////////////////////////////////////////////////////////////////////////////////////////////
// 2014-05-01: Jiao Xianjun (putaoshu@gmail.com)
// to test captured GPS bin here: http://www.jks.com/gps/gps.html

#include <stdio.h>
#include <memory.h>
#include <fftw3.h>
#include <math.h>

#include "gps.h"

///////////////////////////////////////////////////////////////////////////////////////////////

char inline Bipolar(int bit) {
    return bit? -30 : +30;
}


///////////////////////////////////////////////////////////////////////////////////////////////

    const unsigned int PACKET = 871744*64;  // 1/64 original 1bit bin file

    unsigned char rx[PACKET];

static int Sample(char *filename_1bit_bin, char *filename_8bit_bin) {
    const int lo_sin[] = {1,1,0,0}; // Quadrature local oscillators
    const int lo_cos[] = {1,0,0,1};

    const float lo_rate = 4*FC/FS; // NCO rate

    float lo_phase=0; // NCO phase accumulator
    unsigned int i=0, j, k;

    FILE *fp_in, *fp_out;

    fp_in = fopen(filename_1bit_bin, "rb");
    if (fp_in == NULL) {
      printf("can not open file for read!\n");
      return(0);
    }

    fp_out = fopen(filename_8bit_bin, "wb");
    if (fp_out == NULL) {
      printf("can not open file for write!\n");
      return(0);
    }

    char I_byte, Q_byte;
    unsigned run_count = 0;
    while (1) {
        unsigned int read_count = fread(rx, 1, PACKET, fp_in);
        if (read_count != PACKET) {
          printf("seems run out!\n");
          break;
        }
        printf("%d\n", ++run_count);
        for (j=0; j<PACKET; j++) {

            int byte = rx[j];
            for (k=i+8; i<k; i++) {
                int bit = byte&1;
                byte>>=1;

                // Down convert to complex (IQ) baseband by mixing (XORing)
                // samples with quadrature local oscillators
//                fwd_buf[i][0] = Bipolar(bit ^ lo_sin[int(lo_phase)]);
//                fwd_buf[i][1] = Bipolar(bit ^ lo_cos[int(lo_phase)]);
                I_byte = Bipolar(bit ^ lo_sin[int(lo_phase)]);
                fwrite(&I_byte, 1, 1, fp_out);
                Q_byte = Bipolar(bit ^ lo_cos[int(lo_phase)]);
                fwrite(&Q_byte, 1, 1, fp_out);

                lo_phase += lo_rate;
                if (lo_phase>=4) lo_phase-=4;
            }
        }
    }
    fclose(fp_in);
    fclose(fp_out);

    return(0);
}

int main(int argc, char *argv[]) {

    Sample("gps.samples.1bit.I.fs5456.if4092.bin", "gps.samples.8bit.IQinterleave.fs5456.if0.bin");

    return(0);
}
