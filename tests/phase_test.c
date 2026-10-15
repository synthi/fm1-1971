/* SPDX-License-Identifier: GPL-3.0-only */
/* PHASE behavior checks (the CZ-1 side of the old test went with the engine).
 * These are architectural regressions, not hardware audio parity measurements. */
#define main hostsim_main
#include "hostsim.c"
#undef main
static int fails;
static void check(const char *s, int ok) { printf("PHASE: %s %s\n", s, ok ? "ok" : "FAIL"); fails += !ok; }
int main(void)
{
    int maxerr = 0, bounded = 1;
    for (uint32_t w = 0; w < 8; w++) {
        pd_t b; pd_setup(&b, w, 0);
        for (uint32_t ph = 0; ph < 65536; ph += 31) {
            int err = abs(pd_wave(&b, ph) - pd_cos(ph)); if (err > maxerr) maxerr = err;
        }
        for (uint32_t dcw = 0; dcw <= 65535; dcw += 21845) {
            pd_setup(&b, w, dcw);
            for (uint32_t ph = 0; ph < 65536; ph += 13)
                bounded &= abs(pd_wave(&b, ph)) <= 32767;
        }
    }
    printf("PHASE: zero-DCW cosine maximum error %d Q15 units\n", maxerr);
    check("all eight waveforms become cosine at zero DCW", maxerr <= 8);
    check("oscillator corners stay bounded", bounded);
    pd_t b; pd_setup(&b, 0, 65535);
    check("saw reads its first half-cycle faster (Casio PD diagram)", b.x < 32768 && pd_wave(&b, b.x) > 32760);
    for (uint32_t w = 5; w < 8; w++) {
        pd_setup(&b, w, 65535);
        check("resonant sync returns to its baseline", abs(pd_wave(&b, 65535) + 32767) <= 4);
        int smooth = 1;
        for (uint32_t dcw = 0; dcw < 65536; dcw += 4096) {
            pd_setup(&b, w, dcw);
            smooth &= abs(pd_wave(&b, 0) - pd_wave(&b, 65535)) < 8;
        }
        check("fractional resonant cores join smoothly at sync", smooth);
    }
    memset(trk, 0, sizeof trk); host_tracks_init();
    track_t *t = &trk[0]; int32_t out[CTL];
    host_preset(t, 2, 0); t->p[P_E7] = 1; t->p[P_E4] = 12;
    t->p[P_FM1_ATK] = 100; t->p[P_FM2_ATK] = 0;
    t->p[P_FM3_ATK] = 100; t->p[P_FM4_ATK] = 80;
    trk_note_on(t, 60, 100); voice_t *v = &t->v[0];
    track_render(t, out, CTL);
    check("PHASE remains its own engine with six presets", ENGINES[2] == &ENG_PHASE && !strcmp(ENG_PHASE.name,"PHASE") && ENG_PHASE.npresets == 6);
    trk_note_off(t, 60);
    for (uint32_t k = 0; k < FS * 12 / CTL; k++) track_render(t, out, CTL);
    check("voice lifetime follows the render", !v->active);
    host_preset(t, 2, 0); trk_note_on(t, 60, 100); track_render(t, out, CTL);
    voice_kill(&t->v[0]); track_render(t, out, CTL);
    check("shared voice stealing still frees the voice", !t->v[0].active);
    return fails != 0;
}
