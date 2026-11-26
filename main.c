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
    eps = 0.;
    #pragma omp parallel
    {
        int it;
        int done = 0;
        init();
        for (it = 1; it <= itmax; it++)
        {
            relax();
            #pragma omp single copyprivate(done)
            {
                printf("it=%4i   eps=%.12e\n", it, eps);
                done = eps < maxeps;
                eps = 0.;
            }
            if (done) break;
        }
        verify();
    }
    return 0;
}

void init(void)
{
    #pragma omp for collapse(2) firstprivate(i)
    for (k = 0; k < N; ++k)
    for (j = 0; j < N; ++j)
    for (i = 0; i < N; ++i)
    {
        // cannot make ith dimentions parallel (i - 1) dependency
        double x = (double)i / (N - 1);
        double y = (double)j / (N - 1);
        double z = (double)k / (N - 1);
        double r2 = (x - 0.5) * (x - 0.5) + (y - 0.5) * (y - 0.5);
        if (!Active(i, j, k))
            A[k][j][i] = 0.1 + 0.25 * exp(-r2) * cos(z);
        else
            A[k][j][i] = 0.7 * (2.0 + sin(3.0 * z) + cos(x))
                        + 0.3 * A[k][j][i - 1];
    }
}

void relax(void)
{
    {
        int hyper = 0;
        for (hyper = 0; hyper < N + N + N; ++hyper) {
            #pragma omp for collapse(2) firstprivate(k) reduction(max:eps)
            for (j = 1; j < N; j++)
            for (i = 1; i < N; i++)
            {
                k = hyper - i - j;
                if (!(0 <= k && k < N)) {
                    // there will be lots of reduntant iteration
                    continue;
                }
                double x, y, z, cx, cy, cz, old, b;
                if (!Active(i, j, k)) continue;
                x = (double)i / (N - 1);
                y = (double)j / (N - 1);
                z = (double)k / (N - 1);
                cx = 1.0 + 0.1 * cos(x);
                cy = 0.8 + 0.1 * sin(y);
                cz = 0.6 + 0.1 * exp(-z);
                old = A[k][j][i];
                b = (cx * (A[k][j][i - 1] + A[k][j][i + 1])
                    + cy * (A[k][j - 1][i] + A[k][j + 1][i])
                    + cz * (A[k - 1][j][i] + A[k + 1][j][i])
                    + 0.4 * sin(z) * cos(x + y)) / (2.0 * (cx + cy + cz) + 0.4);
                A[k][j][i] = old + 0.79 * (b - old);
                eps = Max(eps, fabs(A[k][j][i] - old));
            }
        }
    }
}

double s = 0.;
void verify(void)
{
    // no data dependancy
    #pragma omp for collapse(3) reduction(+:s)
    for (k = 0; k < N; k++)
    for (j = 0; j < N; j++)
    for (i = 0; i < N; i++)
        s += A[k][j][i] * (i + 1) * (j + 1) * (k + 1)
             / ((double)N * N * N);
    #pragma omp single
    printf("S=%.12e\n", s);
}

