///////////////////////////////////////////////////////////////////////////////////////////////
// Homemade GPS Receiver
// Copyright (c) Andrew Holme 2011-2013
// http://www.holmea.demon.co.uk/GPS/Main.htm
///////////////////////////////////////////////////////////////////////////////////////////////

#include <unistd.h>
#include <stdio.h>
#include <math.h>

#include "LiquidCrystal.h"
#include "gps.h"
#include "spi.h"

///////////////////////////////////////////////////////////////////////////////////////////////

enum {
    LCD_D4=0, LCD_D5=1, LCD_D6=2, LCD_D7=3,
    LCD_EN=4,
    LCD_RS=5
};

///////////////////////////////////////////////////////////////////////////////////////////////

void Print::digitalWrite(int pin, int state) {
    static int reg;
    reg&=~(1<<pin);
    reg|=state<<pin;
    if (pin==LCD_EN) spi_set(CmdSetLCD, reg);
}

void Print::delayMicroseconds(int n) {
    if (n>1) usleep(n);
}

///////////////////////////////////////////////////////////////////////////////////////////////

struct DISPLAY : LiquidCrystal {
    DISPLAY () : LiquidCrystal(LCD_RS, LCD_EN, LCD_D4, LCD_D5, LCD_D6, LCD_D7) {
        begin(16, 2);
        createBars();
    }

    void drawForm(int);
    void drawData(int);
    void createBars();
    void writeAt(int x, int y, const char *s);
};

///////////////////////////////////////////////////////////////////////////////////////////////

const char *Week[] = {
    "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"
};

///////////////////////////////////////////////////////////////////////////////////////////////

struct UMS {
    int u, m;
    double s;
    UMS(double x) {
        u = trunc(x); x = (x-u)*60;
        m = trunc(x); s = (x-m)*60;
    }
};

///////////////////////////////////////////////////////////////////////////////////////////////

static int    StatBars[NUM_CHANS];

static double StatSNR, StatSec, StatLat, StatLon, StatAlt;
static int    StatPRN, StatDay, StatNS,  StatEW,  StatChans;

///////////////////////////////////////////////////////////////////////////////////////////////

void UserStat(STAT st, double d, int i) {
    switch(st) {
        case STAT_PRN:
            StatPRN = i;
            StatSNR = d;
            EventRaise(EVT_PRN);
            break;
        case STAT_POWER:
            StatBars[i] = MIN(sqrt(d)/300,7);
            EventRaise(EVT_BARS);
            break;
        case STAT_LAT:
            StatLat = fabs(d);
            StatNS = d<0?'S':'N';
            break;
        case STAT_LON:
            StatLon = fabs(d);
            StatEW = d<0?'W':'E';
            break;
        case STAT_ALT:
            StatAlt = d;
            StatChans = i;
            EventRaise(EVT_POS);
            break;
        case STAT_TIME:
            StatDay = d/(60*60*24);
            StatSec = d-(60*60*24)*StatDay;
            EventRaise(EVT_TIME);
            break;
    }
}

///////////////////////////////////////////////////////////////////////////////////////////////

void DISPLAY::writeAt(int x, int y, const char *s) {
    setCursor(x, y);
    while(*s) write(*s++);
}

///////////////////////////////////////////////////////////////////////////////////////////////

void DISPLAY::createBars() {
    const char *bars[8] = {
        "\x00\x00\x00\x00\x00\x00\x00\x1f",
        "\x00\x00\x00\x00\x00\x00\x1f\x1f",
        "\x00\x00\x00\x00\x00\x1f\x1f\x1f",
        "\x00\x00\x00\x00\x1f\x1f\x1f\x1f",
        "\x00\x00\x00\x1f\x1f\x1f\x1f\x1f",
        "\x00\x00\x1f\x1f\x1f\x1f\x1f\x1f",
        "\x00\x1f\x1f\x1f\x1f\x1f\x1f\x1f",
        "\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f"
    };

    for (int i=0; i<8; i++)
        createChar(i, (uint8_t*) bars[i]);
 }

///////////////////////////////////////////////////////////////////////////////////////////////

void DISPLAY::drawForm(int page) {
    clear();
    switch(page) {
        case -2:
            writeAt(0, 0, "  Homemade GPS  ");
            writeAt(0, 1, "A.Holme May 2013");
            break;
        case -1:
            writeAt(0, 0, "Shutdown");
            break;
        case 0:
            writeAt(0, 0, "PRN __ ___");
            writeAt(0, 1, "____________");
            break;
        case 1:
            writeAt(0, 0, "_     __._____ _");
            writeAt(0, 1, "_     __._____ _");
            break;
        case 2:
            writeAt(0, 0, "__\xDF __\xDF __.___ _");
            writeAt(0, 1, "__\xDF __\xDF __.___ _");
            break;
        case 3:
            break;
    }
}

///////////////////////////////////////////////////////////////////////////////////////////////

void DISPLAY::drawData(int page) {
    char s[80];
    switch(page) {
        case 0:
            if (EventCatch(EVT_PRN)) {
                sprintf(s, "%2d %3.0f", StatPRN, StatSNR);
                writeAt(4, 0, s);
            }
            if (EventCatch(EVT_BARS)) {
                setCursor(0, 1);
                for (int i=0; i<NUM_CHANS; i++) write(StatBars[i]);
            }
            break;
        case 1:
            if (EventCatch(EVT_POS)) {
                sprintf(s, "%-5d %8.5f %c", StatChans, StatLat, StatNS);
                writeAt(0, 0, s);
                sprintf(s, "%-5.0f %8.5f %c", StatAlt, StatLon, StatEW);
                writeAt(0, 1, s);
            }
            break;
        case 2:
            if (EventCatch(EVT_POS)) {
                UMS lat(StatLat), lon(StatLon);
                sprintf(s, "%2d\xDF%3d\xDF%7.3f %c", lat.u, lat.m, lat.s, StatNS);
                writeAt(0, 0, s);
                sprintf(s, "%2d\xDF%3d\xDF%7.3f %c", lon.u, lon.m, lon.s, StatEW);
                writeAt(0, 1, s);
            }
            break;
        case 3:
            if (EventCatch(EVT_TIME)) {
                UMS hms(StatSec/60/60);
                sprintf(s, "%s %02d:%02d:%02.0f", Week[StatDay], hms.u, hms.m, hms.s);
                writeAt(0, 0, s);
            }
    }
}

///////////////////////////////////////////////////////////////////////////////////////////////

void UserTask() {
    DISPLAY lcd;
    int page=0;

    lcd.drawForm(-2);
    for (int i=0; i<30; i++) {
        TimerWait(100);
        if (EventCatch(JOY_MASK)) {
            EventRaise(EVT_EXIT);
            for (;;) NextTask();
        }
    }
    lcd.drawForm(page);
    for (;;) {
        switch (EventCatch(JOY_MASK)) {
            case JOY_UP:
                if (page>0) lcd.drawForm(--page);
                break;
            case JOY_DOWN:
                if (page<3) lcd.drawForm(++page);
                break;
            case JOY_PUSH:
                lcd.drawForm(-1);
                EventRaise(EVT_EXIT+EVT_SHUTDOWN);
                for (;;) NextTask();

        }
        lcd.drawData(page);
        NextTask();
    }
}
