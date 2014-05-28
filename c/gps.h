///////////////////////////////////////////////////////////////////////////////////////////////
// Homemade GPS Receiver
// Copyright (c) Andrew Holme 2011-2013
// http://www.holmea.demon.co.uk/GPS/Main.htm
///////////////////////////////////////////////////////////////////////////////////////////////

#include <inttypes.h>

#define MAX(a,b) ((a)>(b)?(a):(b))
#define MIN(a,b) ((a)<(b)?(a):(b))

///////////////////////////////////////////////////////////////////////////////
// Parameters

#define FFT_LEN  40000
#define NUM_SATS    32
#define NUM_CHANS   12

///////////////////////////////////////////////////////////////////////////////
// Frequencies

#define L1 1575.42e6 // L1 carrier
#define FC 2.6e6     // Carrier @ 2nd IF
#define FS 10e6      // Sampling rate
#define CPS 1.023e6  // Chip rate
#define BPS 50.0     // NAV data rate

///////////////////////////////////////////////////////////////////////////////
// Official GPS constants

const double PI = 3.1415926535898;

const double MU = 3.986005e14;          // WGS 84: earth's gravitational constant for GPS user
const double OMEGA_E = 7.2921151467e-5; // WGS 84: earth's rotation rate

const double C = 2.99792458e8; // Speed of light

const double F = -4.442807633e-10; // -2*sqrt(MU)/pow(C,2)

//////////////////////////////////////////////////////////////
// Events

#define JOY_MASK 0x1F

#define JOY_RIGHT    (1<<0)
#define JOY_LEFT     (1<<1)
#define JOY_DOWN     (1<<2)
#define JOY_UP       (1<<3)
#define JOY_PUSH     (1<<4)
#define EVT_EXIT     (1<<5)
#define EVT_BARS     (1<<6)
#define EVT_POS      (1<<7)
#define EVT_TIME     (1<<8)
#define EVT_PRN      (1<<9)
#define EVT_SHUTDOWN (1<<10)

//////////////////////////////////////////////////////////////
// Coroutines

unsigned EventCatch(unsigned);
void     EventRaise(unsigned);
void     NextTask();
void     CreateTask(void (*entry)());
unsigned Microseconds(void);
void     TimerWait(unsigned ms);

//////////////////////////////////////////////////////////////
// BCM2835 peripherals

enum SPI_SEL {
    SPI_CS0=0,  // Load embedded CPU image
    SPI_CS1=1   // Host messaging
};

int  peri_init();
void peri_free();
void peri_spi(SPI_SEL sel, char *mosi, int txlen, char *miso, int rxlen);

//////////////////////////////////////////////////////////////
// Search

int  SearchInit();
void SearchFree();
void SearchTask();
void SearchEnable(int sv);
int  SearchCode(int sv, int g1);

//////////////////////////////////////////////////////////////
// Tracking

void ChanTask(void);
int  ChanReset(void);
void ChanStart(int ch, int sv, int t_sample, int taps, int lo_shift, int ca_shift);
bool ChanSnapshot(int ch, uint16_t wpos, int *p_sv, int *p_bits, float *p_pwr);

//////////////////////////////////////////////////////////////
// Solution

void SolveTask();

//////////////////////////////////////////////////////////////
// User interface

enum STAT {
    STAT_PRN,
    STAT_POWER,
    STAT_LAT,
    STAT_LON,
    STAT_ALT,
    STAT_TIME
};

void UserTask();
void UserStat(STAT st, double, int=0);
