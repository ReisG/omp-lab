#include <math.h>
#include <stdlib.h>
#include <stdio.h>

#define Max(a,b) ((a)>(b)?(a):(b))
#ifndef N
#define N (2*2*2*2*2*2+2)
#endif
#ifndef ITMAX
#define ITMAX 100
#endif

double maxeps = 1e-8;
int itmax = ITMAX;
int i, j, k;
double eps;
double A[N][N][N];

inline int Active(int i, int j, int k) {
    double x = (double)i / (N - 1);
    double y = (double)j / (N - 1);
    double z = (double)k / (N - 1);
    double r2 = (x - 0.5) * (x - 0.5) + (y - 0.5) * (y - 0.5);
    return i > 0 && j > 0 && k > 0 &&
        i < N - 1 && j < N - 1 && k < N - 1 &&
        r2 > 0.035 && r2 < 0.22 &&
        k > N / 5 && k < 4 * N / 5;
}

void init(void);
void relax(void);
void verify(void);

int main(void)
{
    int it;
    init();
    for (it = 1; it <= itmax; it++)
    {
        eps = 0.;
        relax();
        printf("it=%4i   eps=%.12e\n", it, eps);
        if (eps < maxeps) break;
    }
    verify();
    return 0;
}

void init(void)
{
    for (k = 0; k < N; k++)
    for (j = 0; j < N; j++)
    for (i = 0; i < N; i++)
    {
        double x = (double)i / (N - 1);
        double y = (double)j / (N - 1);
        double z = (double)k / (N - 1);
        double r2 = (x - 0.5) * (x - 0.5) + (y - 0.5) * (y - 0.5);
        if (!Active(i, j, k))
            A[i][j][k] = 0.1 + 0.25 * exp(-r2) * cos(z);
        else
            A[i][j][k] = 0.7 * (2.0 + sin(3.0 * z) + cos(x))
                        + 0.3 * A[i - 1][j][k];
    }
}

void relax(void)
{
    for (k = 1; k < N - 1; k++)
    for (j = 1; j < N - 1; j++)
    for (i = 1; i < N - 1; i++)
    {
        double x, y, z, cx, cy, cz, old, b;
        if (!Active(i, j, k)) continue;
        x = (double)i / (N - 1);
        y = (double)j / (N - 1);
        z = (double)k / (N - 1);
        cx = 1.0 + 0.1 * cos(x);
        cy = 0.8 + 0.1 * sin(y);
        cz = 0.6 + 0.1 * exp(-z);
        old = A[i][j][k];
        b = (cx * (A[i - 1][j][k] + A[i + 1][j][k])
           + cy * (A[i][j - 1][k] + A[i][j + 1][k])
           + cz * (A[i][j][k - 1] + A[i][j][k + 1])
           + 0.4 * sin(z) * cos(x + y)) / (2.0 * (cx + cy + cz) + 0.4);
        A[i][j][k] = old + 0.79 * (b - old);
        eps = Max(eps, fabs(A[i][j][k] - old));
    }
}

void verify(void)
{
    double s = 0.;
    for (i = 0; i < N; i++)
    for (j = 0; j < N; j++)
    for (k = 0; k < N; k++)
        s += A[i][j][k] * (i + 1) * (j + 1) * (k + 1)
             / ((double)N * N * N);
    printf("S=%.12e\n", s);
}

