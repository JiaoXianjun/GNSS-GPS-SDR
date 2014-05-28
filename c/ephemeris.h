///////////////////////////////////////////////////////////////////////////////////////////////
// Homemade GPS Receiver
// Copyright (c) Andrew Holme 2011-2013
// http://www.holmea.demon.co.uk/GPS/Main.htm
///////////////////////////////////////////////////////////////////////////////////////////////

class EPHEM {

    // Subframe 1
    unsigned week, IODC, t_oc;
    double t_gd, a_f[3];

    // Subframe 2
    unsigned IODE2, t_oe;
    double C_rs, dn, M_0, C_uc, e, C_us, sqrtA, A;

    // Subframe 3
    unsigned IODE3;
    double C_ic, OMEGA_0, C_is, i_0, C_rc, omega, OMEGA_dot, IDOT;

    // Subframe 4, page 18 - Ionospheric delay
    double alpha[4], beta[4];
    void LoadPage18(char *nav);

    void Subframe1(char *nav);
    void Subframe2(char *nav);
    void Subframe3(char *nav);
    void Subframe4(char *nav);
//  void Subframe5(char *nav);

    double EccentricAnomaly(double t_k);

public:
    unsigned tow;

    void   Subframe(char *buf);
    bool   Valid();
    double GetClockCorrection(double t);
    void   GetXYZ(double *x, double *y, double *z, double t);
};

extern EPHEM Ephemeris[];
