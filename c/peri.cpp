///////////////////////////////////////////////////////////////////////////////////////////////
// Homemade GPS Receiver
// Copyright (c) Andrew Holme 2011-2013
// http://www.holmea.demon.co.uk/GPS/Main.htm
///////////////////////////////////////////////////////////////////////////////////////////////

#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>

#include "gps.h"

///////////////////////////////////////////////////////////////////////////////////////////////
// BCM2835 peripherals

#define PERI_BASE   0x20000000
#define GPIO_BASE  (PERI_BASE + 0x200000)
#define SPI0_BASE  (PERI_BASE + 0x204000)

#define BLOCK_SIZE (4*1024)

#define SPI_CS    spi[0]
#define SPI_FIFO  spi[1]
#define SPI_CLK   spi[2]

#define GP_FSEL0 gpio[0]
#define GP_FSEL1 gpio[1]
#define GP_SET0  gpio[7]
#define GP_CLR0 gpio[10]
#define GP_LEV0 gpio[13]

volatile unsigned *gpio, *spi;

///////////////////////////////////////////////////////////////////////////////////////////////
// Frac7 FPGA - Raspberry Pi GPIO

#define FPGA_SCLK    11
#define FPGA_MOSI    10
#define FPGA_MISO     9
#define FPGA_CS_0     8
#define FPGA_CS_1     7

#define FPGA_INIT_B   9
#define FPGA_PROG     4

///////////////////////////////////////////////////////////////////////////////////////////////

int peri_init() {
    int mem_fd;

    mem_fd = open("/dev/mem", O_RDWR|O_SYNC);
    if (mem_fd<0) return -1;

    gpio = (volatile unsigned *) mmap(
        NULL,
        BLOCK_SIZE,
        PROT_READ|PROT_WRITE,
        MAP_SHARED,
        mem_fd,
        GPIO_BASE
    );

    spi = (volatile unsigned *) mmap(
        NULL,
        BLOCK_SIZE,
        PROT_READ|PROT_WRITE,
        MAP_SHARED,
        mem_fd,
        SPI0_BASE
    );

    close(mem_fd);

    if (!gpio) return -2;
    if (!spi)  return -3;

    SPI_CLK = 32;   // SCLK ~ 8 MHz
    SPI_CS = 3<<4;  // Reset

    // GPIO[9:0] function select
    GP_FSEL0 = (1<<(3*FPGA_PROG)) + // 1 = output
               (4<<(3*FPGA_MISO)) + // 4 = alt function 1 (spi)
               (4<<(3*FPGA_CS_0)) +
               (4<<(3*FPGA_CS_1));

    // GPIO[19:10]
    GP_FSEL1 = (4<<(3*(FPGA_MOSI-10))) +
               (4<<(3*(FPGA_SCLK-10)));

    // Reset FPGA
    GP_SET0 = 1<<FPGA_PROG;
    while ((GP_LEV0 & (1<<FPGA_INIT_B)) != 0);
    GP_CLR0 = 1<<FPGA_PROG;
    while ((GP_LEV0 & (1<<FPGA_INIT_B)) == 0);

    return 0;
}

///////////////////////////////////////////////////////////////////////////////////////////////

void peri_spi(SPI_SEL sel, char *mosi, int txlen, char *miso, int rxlen) {
    int rx=0, tx=0;

    SPI_CS = sel + (1<<7);

    while (tx<txlen) {
        if (SPI_CS & (1<<18)) SPI_FIFO = mosi[tx++];
        if (SPI_CS & (1<<17)) miso[rx++] = SPI_FIFO;
    }
    while (tx<rxlen) {
        if (SPI_CS & (1<<18)) SPI_FIFO = 0, tx++;
        if (SPI_CS & (1<<17)) miso[rx++] = SPI_FIFO;
    }
    while (rx<rxlen) {
        if (SPI_CS & (1<<17)) miso[rx++] = SPI_FIFO;
    }

    SPI_CS = 0;
}

///////////////////////////////////////////////////////////////////////////////////////////////

void peri_free() {
    munmap((void *) gpio, BLOCK_SIZE);
    munmap((void *) spi,  BLOCK_SIZE);
}
