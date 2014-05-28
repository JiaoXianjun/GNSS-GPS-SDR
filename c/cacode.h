///////////////////////////////////////////////////////////////////////////////////////////////
// Homemade GPS Receiver
// Copyright (c) Andrew Holme 2011-2013
// http://www.holmea.demon.co.uk/GPS/Main.htm
///////////////////////////////////////////////////////////////////////////////////////////////

#include <memory.h>

struct CACODE {
   char g1[11], g2[11], *tap[2];

   CACODE(int t0, int t1) {
      tap[0] = g2+t0;
      tap[1] = g2+t1;
      memset(g1+1, 1, 10);
      memset(g2+1, 1, 10);
   }

   int Chip() {
      return g1[10] ^ *tap[0] ^ *tap[1];
   }

   void Clock() {
      g1[0] = g1[3] ^ g1[10];
      g2[0] = g2[2] ^ g2[3] ^ g2[6] ^ g2[8] ^ g2[9] ^ g2[10];
      memmove(g1+1, g1, 10);
      memmove(g2+1, g2, 10);
   }

   unsigned GetG1() {
      unsigned ret=0;
      for (int bit=0; bit<10; bit++) ret += ret + g1[10-bit];
      return ret;
   }
};
