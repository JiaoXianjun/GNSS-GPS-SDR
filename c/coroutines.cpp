///////////////////////////////////////////////////////////////////////////////////////////////
// Homemade GPS Receiver
// Copyright (c) Andrew Holme 2011-2013
// http://www.holmea.demon.co.uk/GPS/Main.htm
///////////////////////////////////////////////////////////////////////////////////////////////

#include <setjmp.h>
#include <time.h>

#define STACK_SIZE 8192
#define MAX_TASKS 20

struct TASK {
    int stk[STACK_SIZE];
    union {
        jmp_buf jb;
        struct {
            void *v[6], *sl, *fp, *sp, (*pc)();
        };
    };
};

static TASK Tasks[MAX_TASKS];
static int NumTasks=1;
static unsigned Signals;

void NextTask() {
    static int id;
    if (setjmp(Tasks[id].jb)) return;
    if (++id==NumTasks) id=0;
    longjmp(Tasks[id].jb, 1);
}

void CreateTask(void (*entry)()) {
    TASK *t = Tasks + NumTasks++;
    t->pc = entry;
    t->sp = t->stk + STACK_SIZE-2;
}

unsigned Microseconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return ts.tv_sec*1000000 + ts.tv_nsec/1000;
}

void TimerWait(unsigned ms) {
    unsigned finish = Microseconds() + 1000*ms;
    for (;;) {
        NextTask();
        int diff = finish - Microseconds();
        if (diff<=0) break;
    }
}

void EventRaise(unsigned sigs) {
    Signals |= sigs;
}

unsigned EventCatch(unsigned sigs) {
    sigs &= Signals;
    Signals -= sigs;
    return sigs;
}
