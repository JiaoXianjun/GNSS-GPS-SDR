
const int OUTPUT=0, LOW=0, HIGH=1;

struct Print {
    void pinMode(int, int) {}
    void digitalWrite(int, int);
    void delayMicroseconds(int);
};
