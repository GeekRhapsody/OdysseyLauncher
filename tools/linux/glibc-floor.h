/* Included in every C file of the FFmpeg tools/linux/setup.sh builds, to keep it to the AppImage's glibc floor, 2.34
   (docs/ARCHITECTURE.md decisions log, 2026-11-02). glibc 2.35 gave hypot a new symbol version; the old one, which
   every glibc since 2.2.5 has, does the same job. */
__asm__(".symver hypot,hypot@GLIBC_2.2.5");
