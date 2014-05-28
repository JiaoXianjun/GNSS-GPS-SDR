///////////////////////////////////////////////////////////////////////////////////////////////
// Homemade GPS Receiver
// Copyright (c) Andrew Holme 2011-2013
// http://www.holmea.demon.co.uk/GPS/Main.htm
///////////////////////////////////////////////////////////////////////////////////////////////

#include <inttypes.h>

enum SPI_CMD { // Embedded CPU commands
    CmdSample,
    CmdSetMask,
    CmdSetRateCA,
    CmdSetRateLO,
    CmdSetGainCA,
    CmdSetGainLO,
    CmdSetSV,
    CmdPause,
    CmdSetVCO,
    CmdGetSamples,
    CmdGetChan,
    CmdGetClocks,
    CmdGetGlitches,
    CmdSetDAC,
    CmdSetLCD,
    CmdGetJoy
};

union SPI_MOSI {
    char msg[1];
    struct {
        uint16_t cmd;
        uint16_t wparam;
        uint32_t lparam;
        uint8_t _pad_; // 3 LSBs stay in ha_disr[2:0]
    };
    SPI_MOSI(uint16_t c, uint16_t w=0, uint32_t l=0) :
        cmd(c), wparam(w), lparam(l), _pad_(0) {}
};

struct SPI_MISO {
    char _align_;
    union {
        char msg[1];
        struct {
            char status;
            union {
                char byte[2048];
                uint16_t word[1];
            };
        }__attribute__((packed));
    };
    int len;
}__attribute__((packed));

void spi_set(SPI_CMD cmd, uint16_t wparam=0, uint32_t lparam=0);
void spi_get(SPI_CMD cmd, SPI_MISO *rx, int bytes, uint16_t wparam=0);
void spi_hog(SPI_CMD cmd, SPI_MISO *rx, int bytes);
