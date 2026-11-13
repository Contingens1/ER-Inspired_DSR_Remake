// er_engine - loader modu "ER engine" dla Dark Souls Remastered (proxy dinput8.dll).
// Etap 0: przekazuje DirectInput8Create do systemowego dinput8.dll i loguje stan procesu.
// Hooki mechanik (skok z miejsca, estus w ruchu, roll-strafe) dochodza w etapie 2.
#include <windows.h>
#include <cstdio>
#include <cstdarg>
#include <share.h>
#include <string>
#include <cmath>
#include <cfloat>
#include <vector>
#include <xinput.h>
#include "MinHook.h"

static HMODULE g_real = nullptr;
// ER_DIAG=1 (domyslnie): sondy, zrzut .text, logi testowe. Wydanie: /DER_DIAG=0 (build.bat release).
#ifndef ER_DIAG
#define ER_DIAG 1
#endif
constexpr bool kDiag = ER_DIAG != 0;

static FILE* g_log = nullptr;
static char g_dir[MAX_PATH];  // katalog z DLL (log, zrzuty)

// Log: start gry idzie od razu do pliku. Od pierwszej klatki gry wpisy trafiaja do bufora w pamieci
// (ostatnie kLogRingLines linii) i NIE sa zapisywane - plik nie rosnie. F8 zrzuca bufor do pliku
// (historia sprzed znacznika) i przez kLogAfterMs pisze dalej wprost (to, co dzieje sie tuz po nim).
constexpr int kLogRingLines = 6000, kLogLineLen = 240;
constexpr DWORD kLogAfterMs = 3000;
static char g_logRing[kLogRingLines][kLogLineLen];
static int g_logRingNext = 0, g_logRingCount = 0;
static bool g_logToRing = false;
static DWORD g_logDirectUntil = 0;
static CRITICAL_SECTION g_logLock;
static bool g_logLockReady = false;

static void Log(const char* fmt, ...) {
    if (!g_log || !g_logLockReady) return;
    char line[kLogLineLen];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf_s(line, sizeof(line), _TRUNCATE, fmt, ap);
    va_end(ap);
    EnterCriticalSection(&g_logLock);
    if (g_logToRing && GetTickCount() >= g_logDirectUntil) {
        strcpy_s(g_logRing[g_logRingNext], line);
        g_logRingNext = (g_logRingNext + 1) % kLogRingLines;
        if (g_logRingCount < kLogRingLines) ++g_logRingCount;
    } else {
        fputs(line, g_log);
        fputc('\n', g_log);
        fflush(g_log);
    }
    LeaveCriticalSection(&g_logLock);
}

// F8: historia z bufora do pliku + okno zapisu wprost.
static void LogDump() {
    if (!g_log || !g_logLockReady) return;
    EnterCriticalSection(&g_logLock);
    fprintf(g_log, "----- zrzut bufora: %d linii sprzed znacznika -----\n", g_logRingCount);
    int start = (g_logRingNext - g_logRingCount + kLogRingLines) % kLogRingLines;
    for (int i = 0; i < g_logRingCount; ++i) {
        fputs(g_logRing[(start + i) % kLogRingLines], g_log);
        fputc('\n', g_log);
    }
    g_logRingCount = 0;
    g_logDirectUntil = GetTickCount() + kLogAfterMs;
    fflush(g_log);
    LeaveCriticalSection(&g_logLock);
}

static void OpenLog(HMODULE self) {
    char path[MAX_PATH];
    GetModuleFileNameA(self, path, MAX_PATH);
    char* slash = strrchr(path, '\\');
    if (slash) {
        slash[1] = 0;
        strcpy_s(g_dir, path);
        strcpy_s(slash + 1, path + MAX_PATH - (slash + 1), "er_engine.log");
    }
    // Dopisywanie (kolejne sesje w jednym pliku, np. testy A/B); czytelny w trakcie gry.
    InitializeCriticalSection(&g_logLock);
    g_logLockReady = true;
    g_log = _fsopen(path, "a", _SH_DENYNO);
    if (g_log) {
        char cmd[512] = {};
        strncpy_s(cmd, GetCommandLineA(), _TRUNCATE);
        fprintf(g_log, "\n########## NOWA SESJA (tick %lu) ##########\n", GetTickCount());
    }
}

static bool LoadReal() {
    if (g_real) return true;
    char sys[MAX_PATH];
    GetSystemDirectoryA(sys, MAX_PATH);
    strcat_s(sys, "\\dinput8.dll");
    g_real = LoadLibraryA(sys);
    Log("system dinput8: %s -> %p", sys, g_real);
    return g_real != nullptr;
}

static void DescribeProcess() {
    auto base = reinterpret_cast<BYTE*>(GetModuleHandleA(nullptr));
    auto dos = reinterpret_cast<IMAGE_DOS_HEADER*>(base);
    auto nt = reinterpret_cast<IMAGE_NT_HEADERS64*>(base + dos->e_lfanew);
    Log("exe base %p, timestamp %u, image size %#x", base, nt->FileHeader.TimeDateStamp,
        nt->OptionalHeader.SizeOfImage);
    auto sec = IMAGE_FIRST_SECTION(nt);
    for (int i = 0; i < nt->FileHeader.NumberOfSections; ++i, ++sec)
        Log("  section %-8.8s rva %#010x size %#010x", sec->Name, sec->VirtualAddress, sec->Misc.VirtualSize);
}

// Szuka wzorca bajtow w pierwszej sekcji .text exe ("48 8B ?? 05", ?? = dowolny bajt).
// Uzywane przez hooki etapu 2 - sygnatury zamiast sztywnych adresow.
BYTE* FindPattern(const char* pattern) {
    BYTE pat[256];
    bool any[256];
    int n = 0;
    for (const char* p = pattern; *p && n < 256;) {
        if (*p == ' ') { ++p; continue; }
        if (p[0] == '?') { any[n] = true; pat[n++] = 0; p += (p[1] == '?') ? 2 : 1; continue; }
        any[n] = false;
        pat[n++] = static_cast<BYTE>(strtoul(std::string(p, 2).c_str(), nullptr, 16));
        p += 2;
    }
    auto base = reinterpret_cast<BYTE*>(GetModuleHandleA(nullptr));
    auto nt = reinterpret_cast<IMAGE_NT_HEADERS64*>(base + reinterpret_cast<IMAGE_DOS_HEADER*>(base)->e_lfanew);
    auto sec = IMAGE_FIRST_SECTION(nt);
    BYTE* start = base + sec->VirtualAddress;
    BYTE* end = start + sec->Misc.VirtualSize - n;
    for (BYTE* cur = start; cur < end; ++cur) {
        int i = 0;
        while (i < n && (any[i] || cur[i] == pat[i])) ++i;
        if (i == n) return cur;
    }
    return nullptr;
}


// Arxan trzyma czesc .text zaszyfrowana na dysku i odszyfrowuje ja w pamieci. Czekamy, az
// zapis kierunku przewrotu (RVA 0x398E4F, build A45AAA36...) bedzie czytelny, i zrzucamy
// pierwsza sekcje .text do pliku - do analizy w Ghidrze (tools/splice_text_dump.py).
static void DumpDecryptedText() {
    static const BYTE kRollWrite[] = {0xC6, 0x87, 0x93, 0x00, 0x00, 0x00, 0x01, 0x80, 0x8F, 0xC4, 0x01, 0x00, 0x00, 0x01};
    auto base = reinterpret_cast<BYTE*>(GetModuleHandleA(nullptr));
    auto nt = reinterpret_cast<IMAGE_NT_HEADERS64*>(base + reinterpret_cast<IMAGE_DOS_HEADER*>(base)->e_lfanew);
    auto text = IMAGE_FIRST_SECTION(nt);
    char path[MAX_PATH];
    sprintf_s(path, "%stext_dump_%08x.bin", g_dir, nt->FileHeader.TimeDateStamp);
    if (GetFileAttributesA(path) != INVALID_FILE_ATTRIBUTES) {
        Log("zrzut .text juz istnieje (%s) - pomijam", path);
        return;
    }
    for (int i = 0; i < 240; ++i) {  // do 120 s
        if (memcmp(base + 0x398E4F, kRollWrite, sizeof(kRollWrite)) == 0) {
            Sleep(3000);  // pozostale strony moga odszyfrowywac sie chwile pozniej
            if (FILE* f = _fsopen(path, "wb", _SH_DENYNO)) {
                fwrite(base + text->VirtualAddress, 1, text->Misc.VirtualSize, f);
                fclose(f);
                Log("Arxan odszyfrowany po %d ms; zrzut .text (%#x B) -> %s", i * 500, text->Misc.VirtualSize, path);
            }
            return;
        }
        Sleep(500);
    }
    Log("UWAGA: kod przewrotu nieczytelny po 120 s - inny build exe? zrzut pominiety");
}

// --- Sonda flag zadan akcji (tylko odczyt) -------------------------------------------------
// RVA 0x396860: handler wejscia gracza (ten sam punkt hookuje DSROmniRoll). ctx+0x84..0xBC to
// bajtowe flagi "gracz chce akcji X" (przewrot 0x93-0x96, ...), ctx+0x1C4 bit "jest zadanie".
// Logujemy zmiany flag, zeby przypisac je do przyciskow (skok, estus, sprint).
using InputHandlerFn = void(__fastcall*)(void* ctx, float dt, void* p3);
static InputHandlerFn g_origInput = nullptr;
static BYTE g_prevFlags[0x1C8 - 0x84];
static DWORD g_t0 = 0;

// Zadanie skoku (ustalone sonda + dekompilacja 0x398920): flaga +0xAE, jej licznik czasu
// (float) w +0xF0 + 4*(flaga-0x84), bit "jest zadanie" +0x1C4. Vanilla ustawia +0xAE tylko w
// sprincie (stan ruchu == 3) z wychylona galka - tu wstawiamy je sami z osobnego przycisku.
constexpr int kJumpFlag = 0xAE;
constexpr int kAnyRequest = 0x1C4;

static bool JumpButtonDown() {
    if (GetForegroundWindow() == nullptr) return false;
    DWORD pid = 0;
    GetWindowThreadProcessId(GetForegroundWindow(), &pid);
    if (pid != GetCurrentProcessId()) return false;  // tylko gdy gra ma fokus
    if (GetAsyncKeyState('J') & 0x8000) return true;
    // Pad czytamy przez xinput1_3 zaladowany juz przez gre - bez drugiej wersji XInput w procesie
    // (z dolinkowanym xinput1_4 pad przestawal dzialac w grze).
    using GetStateFn = DWORD(WINAPI*)(DWORD, XINPUT_STATE*);
    static GetStateFn getState = [] {
        HMODULE m = GetModuleHandleA("xinput1_3.dll");
        return m ? reinterpret_cast<GetStateFn>(GetProcAddress(m, "XInputGetState")) : nullptr;
    }();
    XINPUT_STATE xs{};
    return getState && getState(0, &xs) == ERROR_SUCCESS && (xs.Gamepad.wButtons & XINPUT_GAMEPAD_LEFT_THUMB);
}

// Czy gracz wychyla galke/WSAD (ponad martwa strefe) - wybor wariantu skoku.
static bool MovementHeld() {
    for (int k : {'W', 'A', 'S', 'D'})
        if (GetAsyncKeyState(k) & 0x8000) return true;
    using GetStateFn = DWORD(WINAPI*)(DWORD, XINPUT_STATE*);
    static GetStateFn getState = [] {
        HMODULE m = GetModuleHandleA("xinput1_3.dll");
        return m ? reinterpret_cast<GetStateFn>(GetProcAddress(m, "XInputGetState")) : nullptr;
    }();
    XINPUT_STATE xs{};
    if (!getState || getState(0, &xs) != ERROR_SUCCESS) return false;
    float x = xs.Gamepad.sThumbLX, y = xs.Gamepad.sThumbLY;
    return x * x + y * y > 8000.0f * 8000.0f;  // ok. 25% wychylenia
}

// Warianty skoku (animacje dodane przez tools/add_jump_anims.py): 901 z postoju, 902 w ruchu.
// Skok ze sprintu (vanilla) zostaje 900.
constexpr int kJumpAnimVanilla = 900;
constexpr int kJumpAnimStanding = 901;
constexpr int kJumpAnimMoving = 902;
static int g_jumpVariant = kJumpAnimVanilla;

static DWORD g_lastJumpInject = 0;  // GetTickCount() ostatniego wstrzyknietego skoku

// Stan ruchu postaci - getter, ktorego gra uzywa przy skoku ze sprintu (0x398920):
// 0 stoi, 1/2 marsz/bieg, 3 sprint. Argument = p3 handlera wejscia.
using MoveStateFn = char(__fastcall*)(void* p3);

static int PickJumpVariant(void* p3) {
    if (p3) {
        static auto moveState = reinterpret_cast<MoveStateFn>(reinterpret_cast<BYTE*>(GetModuleHandleA(nullptr)) + 0x37BB60);
        char st = moveState(p3);
        if (st == 3) return kJumpAnimVanilla;  // sprint: pelny skok DSR
        return st == 0 ? kJumpAnimStanding : kJumpAnimMoving;
    }
    return MovementHeld() ? kJumpAnimMoving : kJumpAnimStanding;
}

static void InjectStandingJump(BYTE* ctx, float dt, void* p3) {
    static bool wasDown = false;
    bool down = JumpButtonDown();
    if (down && !wasDown) {
        g_lastJumpInject = GetTickCount();
        g_jumpVariant = PickJumpVariant(p3);
        ctx[kJumpFlag] = 1;
        *reinterpret_cast<float*>(ctx + 0xF0 + 4 * (kJumpFlag - 0x84)) = dt;
        ctx[kAnyRequest] |= 1;
        Log("[%7lu ms] wstrzykniete zadanie skoku (+0xAE)", GetTickCount() - g_t0);
    }
    wasDown = down;
}

static void CancelLandingRollIfIdle();  // nizej, przy sondzie PlayAnim
static void AttackSpeedTick(float dt);  // nizej, czasy atakow z ER
static void AirControlTick(float dt);   // nizej, sterowanie w locie
static void AirControlOnPlayAnim(int anim, int layer);
static void PhysProbeTick();            // nizej, sonda fizyki skoku (tylko odczyt)
static void EnemyProbeTick();           // below: enemy attack probe (read-only, ER_DIAG)
static void TargetProbeTick(void* p3);  // below: enemy target / aggro probe (read-only, ER_DIAG)
static void HangProbeTick(const BYTE* ctx, void* p3);  // below: frozen-player probe (read-only, ER_DIAG)
static void AirMomentumTick(float dt);  // nizej, rozped w spadaniu po skoku
static void AirMomentumStart(int anim);
static void AirMomentumOnOtherAnim();
static void* g_momCtx = nullptr;        // ctx i a6 zlecenia skoku - do zakonczenia animacji
static int g_momA6 = 0;
static float PhysF(const BYTE* ph, int off);
static DWORD g_physProbeAt = 0;        // start sondy fizyki (GetTickCount() zlecenia skoku)
static bool g_momEnabled = true;        // F7 (diag) przelacza - test A/B
static void* g_rollCtx = nullptr;       // ctx i a6 ostatniego uniku gracza (diagnoza zawieszenia po uniku)
static int g_rollA6 = 0;
static bool g_momActive = false;        // rozped przejety (faza spadania po skoku)
static int AirAttackSubstitute(void* ctx, int anim, int layer, int a6);  // nizej: atak w locie -> atak z wyskoku ER
static void AirAttackTick(float dt);  // nizej: ladowanie w ataku z wyskoku
static void AirAttackBuffer(BYTE* ctx);  // nizej: klik ataku przed otwarciem okna w skoku
static void AirAttackAfterPlayAnim(int anim, int layer);  // nizej: ladowanie po tym, jak gra konczy atak
static bool g_airAtkMoveLock = false;   // recovery po ladowaniu ataku z wyskoku: osie ruchu = 0
static float g_axis[2] = {};           // ostatnie osie ruchu (hook 0x1A3700/0x1A3750)
static void DrinkDiffProbe(bool itemRequestedNow);  // nizej, sonda roznicowa pamieci

// Sonda uzycia przedmiotu: flaga +0x92 (zadanie uzycia przedmiotu, sonda 2026-11-11).
constexpr int kItemFlag = 0x92;
static DWORD g_lastItemReq = 0;

// --- Bufor uniku (jak w ER) ---------------------------------------------------------------------
// Log 2026-11-12: gra zglasza unik (+0x93) tylko wtedy, gdy w chwili wcisniecia klawisza uniku jest juz
// kierunek. Klawisz uniku wcisniety 15-30 ms PRZED klawiszem kierunku = brak reakcji (ani unik, ani odskok).
// Tu: jesli klawisz uniku poszedl w dol bez kierunku i bez zadania, przez kRollBufferMs czekamy na kierunek
// i wtedy sami wstawiamy zadanie uniku (tak samo jak skok: flaga, licznik czasu, bit "jest zadanie").
// Klawisza uniku nie znamy z konfiguracji gry - uczymy sie go z udanych unikow (ktory klawisz/przycisk
// zmienil stan w klatce, w ktorej gra zglosila unik) i zapisujemy obok DLL.
constexpr int kRollFlag = 0x93;
constexpr DWORD kRollBufferMs = 250;
constexpr DWORD kRollAxisHoldMs = 20;    // kierunek musi trwac tyle, zanim podamy grze wcisniecie uniku
// Bufor v4: zamiast wstawiac flage +0x93 po fakcie (omijalo to DSROmniRoll - unik szedl na wprost), podajemy grze
// jednorazowo "klawisz uniku wlasnie wcisniety" (hook FUN_1401a46b0, akcja 0x5C) w klatce, w ktorej jest juz kierunek.
// Gra sama przechodzi wtedy swoja sciezke uniku przy wcisnieciu (FUN_140398920), razem z hookami DSROmniRoll.
static bool g_fakeRollPress = false;
using RollPressFn = unsigned long long(__fastcall*)(void*);
static RollPressFn g_origRollPress = nullptr;
static unsigned long long __fastcall RollPressDetour(void* p) {
    unsigned long long r = g_origRollPress(p);
    return g_fakeRollPress ? ((r & ~0xFFull) | 1) : r;
}
constexpr DWORD kRollDupMs = 400;        // gra potrafi zglosic unik drugi raz przy puszczeniu klawisza - kasujemy
static DWORD g_rollAxisSince = 0;        // od kiedy kierunek jest wychylony (0 = nie jest)
static DWORD g_rollInjectedAt = 0;
constexpr int kKeyCodes = 256 + 16;      // klawisze/mysz (VK) + 16 przyciskow pada (256 + nr bitu)
static bool g_keyDown[kKeyCodes];
static bool g_keyEdgeDown[kKeyCodes], g_keyEdgeUp[kKeyCodes];
static DWORD g_keyDownAt[kKeyCodes];
static int g_rollKey = -1;
static int g_rollVotes[kKeyCodes];
static DWORD g_rollPendingUntil = 0;
static char g_rollKeyPath[MAX_PATH];
static bool g_rollBufferOn = true;       // F6 (diag) toggles live - A/B test
static bool g_omniRollOn = true;         // F5 (diag) / er_engine.ini [Roll] OmniRoll=1

static BYTE* ChrPosData();               // defined below in AirControl section
static BYTE* g_inputCtx = nullptr;       // local player's input ctx (0x396860)
static void* g_playerAnimCtx = nullptr;  // local player's PlayAnim ctx (g_inputCtx + 0x3A0)
static float g_omniLastStickYaw = 0.0f;
static DWORD g_omniLastStickAt = 0;
static bool g_omniArmed = false;
static float g_omniArmedYaw = 0.0f;
static DWORD g_omniArmedAt = 0;
static bool g_omniActive = false;
static float g_omniActiveYaw = 0.0f;
static float g_omniHoldElapsed = 0.0f;
constexpr DWORD kOmniQueuedMaxMs = 4500; // a queued roll may wait this long (longest knockdown: roll from 3.0 s)
constexpr float kOmniHoldSec = 0.50f;   // covers 0..0.07s pre-JT7 gap + roll travel, ends before ~0.56s cancel window

static bool IsForwardRollAnim(int a) {
    return a == 700 || a == 710 || a == 720 || a == 730 || a == 735;
}

static bool IsLockedOnRollable(const BYTE* ctx, void* p3) {
    if (!ctx || !p3 || ctx[0x350] != 0) return false;  // +0x350 = precision/bow aim mode
    __try {
        auto b = static_cast<const BYTE*>(p3);
        if (b[0x21D] != 0) return false;               // 1 = unlocked free movement, 0 = lock-on strafe
        auto chr = *reinterpret_cast<BYTE* const*>(b + 0x10);
        if (reinterpret_cast<ULONG_PTR>(chr) < 0x10000) return false;
        return chr[0x1A0] != 0;                        // ChrIns+0x1A0 = active lock-on target
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

static void OmniApplyYawNow(float yaw) {
    if (BYTE* pos = ChrPosData()) {
        __try {
            *reinterpret_cast<float*>(pos + 0x04) = yaw;
            *reinterpret_cast<float*>(pos + 0x144) = 0.0f;
        } __except (EXCEPTION_EXECUTE_HANDLER) {}
    }
}

// --- Sprint while locked on (as in ER) ----------------------------------------------------------
// Vanilla (FUN_140398920, branch LAB_140398fa8): with a lock-on target the game raises a side/back roll
// (+0x94..0x96) the moment the roll/sprint key goes down, so holding the key can never become a sprint in
// those directions; only "forward" waits for the key release. Here the roll raised while the key is held is
// dropped and remembered; on release it is raised by the DLL as +0x93 (OmniRollPostInput then gives it the
// stick direction) if the key was held shorter than the game's sprint threshold. A longer hold lets the
// game's own sprint (+0x1E4, driven by the hold timer +0x260) take over.
static bool g_lockSprintOn = true;       // er_engine.ini [Roll] LockOnSprint=1
static bool g_lockRollDeferred = false;

static DWORD SprintHoldThresholdMs() {
    float s = 0.0f;
    __try {
        s = *reinterpret_cast<const float*>(reinterpret_cast<const BYTE*>(GetModuleHandleA(nullptr)) + 0x1A2C0A0);
    } __except (EXCEPTION_EXECUTE_HANDLER) {}
    return (s > 0.05f && s < 2.0f) ? static_cast<DWORD>(s * 1000.0f) : 500;
}

static void LockOnSprintPostInput(BYTE* ctx, float dt, void* p3) {
    if (!g_lockSprintOn || g_rollKey <= 0) { g_lockRollDeferred = false; return; }
    DWORD now = GetTickCount();
    if (g_keyDown[g_rollKey] && IsLockedOnRollable(ctx, p3)) {
        for (int f = 0x94; f <= 0x96; ++f) {
            if (!ctx[f] || g_prevFlags[f - 0x84]) continue;
            ctx[f] = 0;
            *reinterpret_cast<float*>(ctx + 0xF0 + 4 * (f - 0x84)) = 0.0f;
            if (!g_lockRollDeferred)
                Log("[%7lu ms] lock-on sprint: roll +0x%02X deferred to key release (key held %lu ms)", now - g_t0, f,
                    now - g_keyDownAt[g_rollKey]);
            g_lockRollDeferred = true;
        }
    }
    // Forward-ish press: the game raises nothing at key down and waits for the release, where it rolls only
    // if the stick still reads "forward". A stick that crosses the diagonal during the tap falls between
    // the two vanilla paths and the roll is lost (log 2026-11-13: axes 0.65 -0.59 at key down, 0.67 -0.74
    // at release, twice in a row, full stamina). Any press with a direction held is therefore tracked here
    // and rolled on release if the game does not do it itself.
    if (!g_lockRollDeferred && g_keyEdgeDown[g_rollKey] && IsLockedOnRollable(ctx, p3) &&
        sqrtf(g_axis[0] * g_axis[0] + g_axis[1] * g_axis[1]) >= 0.3f) {
        g_lockRollDeferred = true;
        Log("[%7lu ms] lock-on sprint: key down with a direction, no roll raised - roll on release", now - g_t0);
    }
    if (!g_lockRollDeferred) return;
    DWORD held = now - g_keyDownAt[g_rollKey];
    DWORD limit = SprintHoldThresholdMs();
    if (g_keyDown[g_rollKey]) {
        if (held >= limit) {
            g_lockRollDeferred = false;
            Log("[%7lu ms] lock-on sprint: key held %lu ms (limit %lu) - roll dropped, sprint", now - g_t0, held, limit);
        }
        return;
    }
    g_lockRollDeferred = false;
    int stamina = 0;
    __try {
        auto chr = *reinterpret_cast<BYTE* const*>(static_cast<const BYTE*>(p3) + 0x10);
        if (reinterpret_cast<ULONG_PTR>(chr) >= 0x10000) stamina = *reinterpret_cast<const int*>(chr + 0x3F8);
    } __except (EXCEPTION_EXECUTE_HANDLER) {}
    bool roll = held < limit && stamina > 9;
    if (roll && !ctx[kRollFlag]) {
        ctx[kRollFlag] = 1;
        *reinterpret_cast<float*>(ctx + 0xF0 + 4 * (kRollFlag - 0x84)) = dt;
        ctx[kAnyRequest] |= 1;
    }
    ctx[0x329] = 0;  // the game must not raise its own roll-on-release on top of ours
    Log("[%7lu ms] lock-on sprint: key released after %lu ms (limit %lu, stamina %d) - %s", now - g_t0, held, limit,
        stamina, roll ? "roll" : "no roll");
}

// Converts 4-way lock-on roll requests (+0x94 back, +0x95 left, +0x96 right, and queued +0x224)
// into forward roll (+0x93) and arms the exact 360-degree camera-relative world yaw from ctx+0x10/0x18.
static void OmniRollPostInput(BYTE* ctx, float dt, void* p3) {
    g_inputCtx = ctx;
    g_playerAnimCtx = ctx + 0x3A0;
    DWORD now = GetTickCount();
    float wx = *reinterpret_cast<const float*>(ctx + 0x10);
    float wz = *reinterpret_cast<const float*>(ctx + 0x18);
    float wlen2 = wx * wx + wz * wz;
    if (wlen2 > 0.01f) {
        g_omniLastStickYaw = atan2f(-wx, -wz);
        g_omniLastStickAt = now ? now : 1;
    }
    if (!g_omniRollOn) {
        g_omniArmed = false;
        g_omniActive = false;
        return;
    }
    // Without a lock-on target a pending direction must not reach a later roll (queued rolls keep it for
    // up to kOmniQueuedMaxMs).
    if (!IsLockedOnRollable(ctx, p3)) { g_omniArmed = false; return; }

    // Also convert DSR's built-in action queue slot (ctx+0x224: index relative to 0x84) for recovery-queued rolls
    int& queued = *reinterpret_cast<int*>(ctx + 0x224);
    if (queued >= (0x94 - 0x84) && queued <= (0x96 - 0x84)) {
        queued = kRollFlag - 0x84;
    }

    bool converted = false;
    for (int f = 0x94; f <= 0x96; ++f) {
        if (ctx[f]) {
            converted = true;
            ctx[f] = 0;
            *reinterpret_cast<float*>(ctx + 0xF0 + 4 * (f - 0x84)) = 0.0f;
        }
    }
    if (converted) {
        ctx[kRollFlag] = 1;
        *reinterpret_cast<float*>(ctx + 0xF0 + 4 * (kRollFlag - 0x84)) = dt;
        ctx[kAnyRequest] |= 1;
    }

    if (ctx[kRollFlag] && !g_prevFlags[kRollFlag - 0x84]) {
        float yaw = 0.0f;
        if (wlen2 > 0.01f) {
            yaw = atan2f(-wx, -wz);
        } else if (g_omniLastStickAt && now - g_omniLastStickAt < 400) {
            yaw = g_omniLastStickYaw;
        } else if (BYTE* pos = ChrPosData()) {
            __try { yaw = *reinterpret_cast<const float*>(pos + 0x04); } __except (EXCEPTION_EXECUTE_HANDLER) {}
        }
        g_omniArmed = true;
        g_omniArmedYaw = yaw;
        g_omniArmedAt = now;
        if (kDiag)
            Log("[%7lu ms] omniroll: armed yaw=%.3f rad (vec %.2f %.2f, conv=%d)",
                now - g_t0, yaw, wx, wz, converted ? 1 : 0);
    }
}

static void OmniRollOnPlayAnim(void* ctx, int anim, int layer, int a6) {
    bool isPlayer = (g_playerAnimCtx && ctx == g_playerAnimCtx) || (!g_playerAnimCtx && ctx == g_rollCtx);
    if (layer != 7) return;
    if (IsForwardRollAnim(anim) && (!g_playerAnimCtx || ctx == g_playerAnimCtx)) {
        g_rollCtx = ctx;
        g_rollA6 = a6;
        isPlayer = true;
    }
    if (!isPlayer) return;
    if (IsForwardRollAnim(anim)) {
        DWORD now = GetTickCount();
        DWORD age = now - g_omniArmedAt;
        if (g_omniRollOn && g_omniArmed && age <= kOmniQueuedMaxMs) {
            // A roll pressed during a hit reaction or another animation is queued by the game and starts
            // when that animation lets it. With the old 400 ms limit such a roll got no direction at all
            // and went straight ahead (logs 2026-11-13: rolls starting 450-810 ms after the request).
            // A queued roll takes the direction held when it starts, else the one held at the press.
            bool queued = age > 400;
            float yaw = g_omniArmedYaw;
            if (queued && g_omniLastStickAt && now - g_omniLastStickAt < 150) yaw = g_omniLastStickYaw;
            g_omniArmed = false;
            g_omniActive = true;
            g_omniActiveYaw = yaw;
            g_omniHoldElapsed = 0.0f;
            OmniApplyYawNow(g_omniActiveYaw);
            if (kDiag)
                Log("[%7lu ms] omniroll: commit anim=%d yaw=%.3f rad%s", now - g_t0, anim, g_omniActiveYaw,
                    queued ? " (queued roll)" : "");
            if (kDiag && queued) Log("[%7lu ms] omniroll: queued roll started %lu ms after the request", now - g_t0, age);
        } else {
            g_omniActive = false;
        }
    } else {
        // Note: on chained roll (710 -> -1 -> 710), -1 clears g_omniActive while preserving g_omniArmed for the next call
        g_omniActive = false;
    }
}

static bool g_freeStaminaOn = true;  // [Stamina] FreeOutOfCombat (see FreeStaminaTick)
static bool g_itemHitCancelOn = true;  // [Items] HitCancelsItem (see ItemUpperOnPlayAnim)
static DWORD g_itemBrokenAt = 0;       // item use broken by another animation (see DrinkActive)
static bool IsItemWalkAnim(int a);     // defined below in the DrinkSlowWalk section

static void LoadConfigIni() {
    char iniPath[MAX_PATH];
    sprintf_s(iniPath, "%ser_engine.ini", g_dir);
    g_omniRollOn = GetPrivateProfileIntA("Roll", "OmniRoll", 1, iniPath) != 0;
    g_rollBufferOn = GetPrivateProfileIntA("Roll", "RollBuffer", 1, iniPath) != 0;
    g_lockSprintOn = GetPrivateProfileIntA("Roll", "LockOnSprint", 1, iniPath) != 0;
    g_freeStaminaOn = GetPrivateProfileIntA("Stamina", "FreeOutOfCombat", 1, iniPath) != 0;
    g_itemHitCancelOn = GetPrivateProfileIntA("Items", "HitCancelsItem", 1, iniPath) != 0;
    Log("config: OmniRoll=%d RollBuffer=%d LockOnSprint=%d FreeOutOfCombat=%d HitCancelsItem=%d (%s)", g_omniRollOn ? 1 : 0,
        g_rollBufferOn ? 1 : 0, g_lockSprintOn ? 1 : 0, g_freeStaminaOn ? 1 : 0, g_itemHitCancelOn ? 1 : 0, iniPath);
}

static bool IsMoveKey(int c) { return c == 'W' || c == 'A' || c == 'S' || c == 'D'; }

static void PollKeys() {
    memset(g_keyEdgeDown, 0, sizeof(g_keyEdgeDown));
    memset(g_keyEdgeUp, 0, sizeof(g_keyEdgeUp));
    DWORD pid = 0;
    HWND fg = GetForegroundWindow();
    if (fg) GetWindowThreadProcessId(fg, &pid);
    if (pid != GetCurrentProcessId()) return;
    using GetStateFn = DWORD(WINAPI*)(DWORD, XINPUT_STATE*);
    static GetStateFn getState = [] {
        HMODULE m = GetModuleHandleA("xinput1_3.dll");
        return m ? reinterpret_cast<GetStateFn>(GetProcAddress(m, "XInputGetState")) : nullptr;
    }();
    XINPUT_STATE xs{};
    WORD pad = (getState && getState(0, &xs) == ERROR_SUCCESS) ? xs.Gamepad.wButtons : 0;
    DWORD now = GetTickCount();
    for (int c = 1; c < kKeyCodes; ++c) {
        if (c == VK_SHIFT || c == VK_CONTROL || c == VK_MENU || c == 255) continue;  // sa tez jako lewy/prawy
        bool down = c < 256 ? (GetAsyncKeyState(c) & 0x8000) != 0 : (pad >> (c - 256)) & 1;
        if (down == g_keyDown[c]) continue;
        g_keyDown[c] = down;
        if (down) {
            g_keyEdgeDown[c] = true;
            g_keyDownAt[c] = now;
            if (kDiag) Log("[%7lu ms] klawisz 0x%03X w dol | osie %.2f %.2f", now - g_t0, c, g_axis[0], g_axis[1]);
        } else {
            g_keyEdgeUp[c] = true;
            if (kDiag) Log("[%7lu ms] klawisz 0x%03X w gore po %lu ms | osie %.2f %.2f", now - g_t0, c, now - g_keyDownAt[c], g_axis[0], g_axis[1]);
        }
    }
}

static void RollKeyLoad(HMODULE self) {
    GetModuleFileNameA(self, g_rollKeyPath, MAX_PATH);
    char* slash = strrchr(g_rollKeyPath, 92);  // 92 = backslash
    if (!slash) { g_rollKeyPath[0] = 0; return; }
    strcpy_s(slash + 1, MAX_PATH - (slash + 1 - g_rollKeyPath), "er_engine_rollkey.txt");
    FILE* f = nullptr;
    if (fopen_s(&f, g_rollKeyPath, "r") == 0 && f) {
        int k = -1;
        if (fscanf_s(f, "%d", &k) == 1 && k > 0 && k < kKeyCodes) { g_rollKey = k; g_rollVotes[k] = 3; }
        fclose(f);
    }
    Log("bufor uniku: klawisz uniku %s (0x%03X)", g_rollKey > 0 ? "wczytany" : "nieznany - nauczy sie z 3 udanych unikow", g_rollKey > 0 ? g_rollKey : 0);
}

// Diagnostyka: stan gry w chwili wcisniecia klawisza uniku i kazdego zadania uniku. Pola z dekompilacji
// FUN_140398920: p3+0x10 -> +0x3F8 (int, prog "> 9" przy uniku - wyglada na wytrzymalosc), p3+0x21D namierzenie,
// ctx+0x260 czas trzymania klawisza, +0x324/+0x328 odskok, +0x329 "unik takze przy puszczeniu".
static void RollStateLog(const char* what, const BYTE* ctx, void* p3) {
    if (!kDiag) return;
    int sp = -1, lock = -1;
    __try {
        auto b = static_cast<const BYTE*>(p3);
        auto chr = b ? *reinterpret_cast<BYTE* const*>(b + 0x10) : nullptr;
        if (reinterpret_cast<ULONG_PTR>(chr) >= 0x10000) sp = *reinterpret_cast<const int*>(chr + 0x3F8);
        if (b) lock = b[0x21D];
    } __except (EXCEPTION_EXECUTE_HANDLER) {}
    Log("[%7lu ms] unik-stan (%s): +3F8=%d namierzenie=%d trzymanie=%.3f odskok=%.3f/%u przy-puszczeniu=%u osie %.2f %.2f", GetTickCount() - g_t0,
        what, sp, lock, *reinterpret_cast<const float*>(ctx + 0x260), *reinterpret_cast<const float*>(ctx + 0x324), ctx[0x328], ctx[0x329], g_axis[0], g_axis[1]);
}

// Wolane PRZED handlerem gry: czy w tej klatce podac grze wcisniecie klawisza uniku.
static bool RollBufferPre(const BYTE* ctx, void* p3) {
    if (!g_rollPendingUntil || !g_rollBufferOn || !g_origRollPress) return false;
    DWORD now = GetTickCount();
    if (now > g_rollPendingUntil) { g_rollPendingUntil = 0; return false; }
    if (!g_rollAxisSince || now - g_rollAxisSince < kRollAxisHoldMs) return false;
    g_rollPendingUntil = 0;
    g_rollInjectedAt = now;
    RollStateLog("bufor: podaje wcisniecie", ctx, p3);
    Log("[%7lu ms] bufor uniku: podane wcisniecie uniku %lu ms po klawiszu (osie %.2f %.2f)", now - g_t0,
        now - g_keyDownAt[g_rollKey], g_axis[0], g_axis[1]);
    return true;
}

static bool DrinkActive();  // defined below in DrinkSlowWalk section

// While drinking the DLL caps the movement axes to 0.45 (slow walk). The game then treats the roll/sprint
// key as pressed "without direction" (+0x328 = 1 at key down) and raises a backstep request (+0x8E) after
// 0.1 s of holding, or right after a tap; the request is queued and fires in the first cancel window of
// the drink animation (log 2026-11-12: key held with axes 1.00 -> +0x8E -> animation 680 when 7588 ended).
// The player holds a direction, so they mean sprint/roll, never a backstep: drop the request. The grace
// period covers a key pressed while the cap was still on.
constexpr DWORD kDrinkBackstepGraceMs = 250;
static void SuppressSprintWhileDrinking(BYTE* ctx) {
    static DWORD lastDrink = 0;
    if (!ctx) return;
    DWORD now = GetTickCount();
    bool drinking = DrinkActive();
    if (drinking) {
        lastDrink = now ? now : 1;
        ctx[0x1E4] = 0;  // block sprint flag (+0x1E4) so holding sprint button drops to walk during Estus
    }
    if ((drinking || (lastDrink && now - lastDrink < kDrinkBackstepGraceMs)) && ctx[0x8E] &&
        sqrtf(g_axis[0] * g_axis[0] + g_axis[1] * g_axis[1]) >= 0.5f) {
        ctx[0x8E] = 0;
        Log("[%7lu ms] drink: backstep request dropped (direction held, axes %.2f %.2f)", now - g_t0, g_axis[0], g_axis[1]);
    }
}

static void RollBufferTick(BYTE* ctx, float dt, void* p3) {
    bool rise = false;
    for (int f = 0x93; f <= 0x96; ++f) {
        if (ctx[f] && !g_prevFlags[f - 0x84]) { rise = true; break; }
    }
    DWORD now = GetTickCount();
    if (g_rollKey > 0 && g_keyEdgeDown[g_rollKey]) RollStateLog("klawisz w dol", ctx, p3);
    if (g_rollKey > 0 && g_keyEdgeUp[g_rollKey]) RollStateLog("klawisz w gore", ctx, p3);
    if (rise) RollStateLog("zadanie gry", ctx, p3);
    float mag = sqrtf(g_axis[0] * g_axis[0] + g_axis[1] * g_axis[1]);
    if (rise) {
        g_rollPendingUntil = 0;
        // FUN_140398920: przy wcisnieciu gra ustawia +0x329 ("unik takze przy puszczeniu") i przy puszczeniu
        // zglasza unik DRUGI raz. Gra go ignoruje, ale DSROmniRoll uzbraja sie ponownie i porzuca kierunek
        // trwajacego uniku (log: ROLL-TRAJECTORY reason=superseded, potem unik bez kierunku = "na wprost").
        if (g_rollKey > 0 && g_keyDown[g_rollKey] && ctx[0x329]) {
            ctx[0x329] = 0;
            if (kDiag) Log("[%7lu ms] unik: zgaszone +0x329 (bez dubla przy puszczeniu klawisza)", now - g_t0);
        }
        // nauka: ktory klawisz (poza ruchem) zmienil stan w klatce zgloszenia uniku
        for (int c = 1; c < kKeyCodes; ++c) {
            if (IsMoveKey(c) || !(g_keyEdgeDown[c] || g_keyEdgeUp[c])) continue;
            if (++g_rollVotes[c] >= 3 && (g_rollKey < 0 || g_rollVotes[c] > g_rollVotes[g_rollKey] + 2) && c != g_rollKey) {
                g_rollKey = c;
                Log("[%7lu ms] bufor uniku: klawisz uniku = 0x%03X", now - g_t0, c);
                FILE* f = nullptr;
                if (g_rollKeyPath[0] && fopen_s(&f, g_rollKeyPath, "w") == 0 && f) { fprintf(f, "%d\n", c); fclose(f); }
            }
        }
        return;
    }
    if (g_rollKey < 0 || !g_rollBufferOn) return;
    if (g_keyEdgeDown[g_rollKey] && mag < 0.3f) {
        g_rollPendingUntil = now + kRollBufferMs;
        return;
    }
}

static void ForceEndPlayerAnim();  // nizej, przy CancelLandingRollIfIdle

// --- Free stamina out of combat (as in Elden Ring) ----------------------------------------------
// The game has a per-character "no stamina consumption" flag: ChrFlags2 bit 0x400 (DSR-Gadget
// ChrData1+0x514; +0x10 in this exe = chr+0x524 - the input handler tests NoMove 0x200 / NoAttack 0x100
// at chr+0x525). The DLL sets it on the player while out of combat and only while sprinting; any
// full-body animation (roll, jump, attack, cast, item) clears it, so those still cost stamina.
// "In combat" is a heuristic (no enemy list yet): lock-on target, HP lost recently, or attacked recently.
constexpr DWORD kCombatAfterHitMs = 8000;
constexpr DWORD kCombatAfterAttackMs = 5000;
static int g_mainAnim = -1;              // player's current layer-7 animation (-1 = none)
static DWORD g_lastAttackAnimAt = 0;
static BYTE* g_freeStamChr = nullptr;    // character whose flag this DLL set

// 2026-11-13 (player's decision after the first test): only sprinting is free. Rolls, backstep, jumps and
// attacks always cost stamina, so the flag is up only while no full-body animation plays.
static bool IsFreeStaminaAnim(int a) { return a == -1; }

// Called from PlayAnimDetour for the player's layer 7.
static void TrackPlayerMainAnim(int animId, int layer) {
    if (layer != 7) return;
    g_mainAnim = animId;
    if (!IsFreeStaminaAnim(animId)) {
        // Drop the flag right away: the cost of this action may be charged before the next input tick.
        if (g_freeStamChr) __try {
            *reinterpret_cast<DWORD*>(g_freeStamChr + 0x524) &= ~0x400u;
            g_freeStamChr = nullptr;
        } __except (EXCEPTION_EXECUTE_HANDLER) {
        }
        int id = animId % 10000;
        if (animId >= 200000 && id >= 3000 && id < 6000) {  // weapon attack (groups 20-49 and special 12x-14x)
            DWORD now = GetTickCount();
            g_lastAttackAnimAt = now ? now : 1;
        }
    }
}

// Runs after the input handler: the flag is set only in frames where the sprint flag (+0x1E4) is on and
// the handler raised no roll / backstep / jump request (+0x93..0x96, +0x8E, +0xAE) - those requests are
// served later in the frame and must find the flag down.
static void FreeStaminaTick(const BYTE* ctx, void* p3) {
    BYTE*& ours = g_freeStamChr;
    static int lastHp = -1;
    static DWORD lastHpDropAt = 0;
    static int lastState = -1;
    BYTE* chr = nullptr;
    __try {
        chr = *reinterpret_cast<BYTE**>(static_cast<BYTE*>(p3) + 0x10);
        if (reinterpret_cast<ULONG_PTR>(chr) < 0x10000) return;
        DWORD now = GetTickCount();
        int hp = *reinterpret_cast<int*>(chr + 0x3E8);
        if (lastHp >= 0 && hp < lastHp) lastHpDropAt = now ? now : 1;
        lastHp = hp;
        bool locked = chr[0x1A0] != 0;
        bool hit = lastHpDropAt && now - lastHpDropAt < kCombatAfterHitMs;
        bool attacked = g_lastAttackAnimAt && now - g_lastAttackAnimAt < kCombatAfterAttackMs;
        bool combat = locked || hit || attacked;
        bool sprinting = ctx[0x1E4] == 1;
        bool request = ctx[0x8E] || ctx[0x93] || ctx[0x94] || ctx[0x95] || ctx[0x96] || ctx[0xAE];
        bool want = g_freeStaminaOn && !combat && sprinting && !request && IsFreeStaminaAnim(g_mainAnim);
        DWORD* flags = reinterpret_cast<DWORD*>(chr + 0x524);
        if (want) {
            if (!(*flags & 0x400)) { *flags |= 0x400; ours = chr; }
        } else if (ours == chr && (*flags & 0x400)) {
            *flags &= ~0x400u;
            ours = nullptr;
        }
        int state = !g_freeStaminaOn ? 0 : combat ? (locked ? 1 : hit ? 2 : 3) : 4;
        if (state != lastState) {
            static const char* kNames[] = {"off", "combat (lock-on)", "combat (HP lost)", "combat (attacked)",
                                           "out of combat - sprint free"};
            Log("[%7lu ms] stamina: %s (hp %d, stamina %d)", now - g_t0, kNames[state], hp,
                *reinterpret_cast<int*>(chr + 0x3F8));
            lastState = state;
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) {
    }
}

static void __fastcall InputDetour(void* ctx, float dt, void* p3) {
    if (!g_logToRing) { Log("pierwsza klatka gry: dalsze wpisy ida do bufora w pamieci, F8 zrzuca go do pliku"); g_logToRing = true; }
    PollKeys();
    {   // os ruchu sprzed handlera (hooki osi aktualizuja g_axis w trakcie handlera - tu wartosc z poprzedniej klatki)
        float mag = sqrtf(g_axis[0] * g_axis[0] + g_axis[1] * g_axis[1]);
        DWORD now = GetTickCount();
        if (mag < 0.5f) g_rollAxisSince = 0; else if (!g_rollAxisSince) g_rollAxisSince = now ? now : 1;
    }
    g_fakeRollPress = RollBufferPre(static_cast<BYTE*>(ctx), p3);
    g_origInput(ctx, dt, p3);
    g_fakeRollPress = false;
    SuppressSprintWhileDrinking(static_cast<BYTE*>(ctx));
    LockOnSprintPostInput(static_cast<BYTE*>(ctx), dt, p3);
    OmniRollPostInput(static_cast<BYTE*>(ctx), dt, p3);
    RollBufferTick(static_cast<BYTE*>(ctx), dt, p3);
    InjectStandingJump(static_cast<BYTE*>(ctx), dt, p3);
    AirAttackBuffer(static_cast<BYTE*>(ctx));
    FreeStaminaTick(static_cast<const BYTE*>(ctx), p3);
    AttackSpeedTick(dt);
    AirControlTick(dt);
    AirMomentumTick(dt);
    if (kDiag) { PhysProbeTick(); EnemyProbeTick(); TargetProbeTick(p3); HangProbeTick(static_cast<const BYTE*>(ctx), p3); }
    AirAttackTick(dt);
    if (kDiag) {  // F8 = znacznik w logu (podzial testu na kroki)
        static bool f8 = false;
        static int marker = 0;
        bool down = (GetAsyncKeyState(VK_F8) & 0x8000) != 0;
        if (down && !f8) {
            LogDump();
            Log("[%7lu ms] ===== ZNACZNIK %d =====", GetTickCount() - g_t0, ++marker);
            g_physProbeAt = GetTickCount();  // 2.5 s zrzutu fizyki od znacznika (diagnoza zawieszenia postaci)
        }
        f8 = down;
        static bool f7 = false;  // F7 = rozped w spadaniu wl./wyl. (test A/B)
        bool down7 = (GetAsyncKeyState(VK_F7) & 0x8000) != 0;
        if (down7 && !f7) {
            g_momEnabled = !g_momEnabled;
            Log("[%7lu ms] ===== ROZPED W SPADANIU: %s =====", GetTickCount() - g_t0, g_momEnabled ? "WLACZONY" : "WYLACZONY");
        }
        f7 = down7;
        static bool f9 = false;  // F9 = EKSPERYMENT: wymuszony koniec animacji gracza na warstwach 7 i 23 (zawieszenie po uniku)
        bool down9 = (GetAsyncKeyState(VK_F9) & 0x8000) != 0;
        if (down9 && !f9) { ForceEndPlayerAnim(); g_physProbeAt = GetTickCount(); }
        f9 = down9;
        static bool f6 = false;  // F6 = bufor uniku wl./wyl. (test A/B)
        bool down6 = (GetAsyncKeyState(VK_F6) & 0x8000) != 0;
        if (down6 && !f6) {
            g_rollBufferOn = !g_rollBufferOn;
            Log("[%7lu ms] ===== BUFOR UNIKU: %s =====", GetTickCount() - g_t0, g_rollBufferOn ? "WLACZONY" : "WYLACZONY");
        }
        f6 = down6;
        static bool f5 = false;  // F5 = OmniRoll on/off (live A/B test)
        bool down5 = (GetAsyncKeyState(VK_F5) & 0x8000) != 0;
        if (down5 && !f5) {
            g_omniRollOn = !g_omniRollOn;
            if (!g_omniRollOn) { g_omniArmed = false; g_omniActive = false; }
            Log("[%7lu ms] ===== OMNIROLL: %s =====", GetTickCount() - g_t0, g_omniRollOn ? "WLACZONY" : "WYLACZONY");
        }
        f5 = down5;
    }
    CancelLandingRollIfIdle();
    auto flags = static_cast<BYTE*>(ctx) + 0x84;
    bool itemNow = flags[kItemFlag - 0x84] && !g_prevFlags[kItemFlag - 0x84];
    if (itemNow) {
        g_lastItemReq = GetTickCount();
        Log("[%7lu ms] zadanie uzycia przedmiotu (+0x92)", g_lastItemReq - g_t0);
    }
    if (kDiag) DrinkDiffProbe(itemNow);
    char line[512];
    int len = 0;
    for (int i = 0; i < static_cast<int>(sizeof(g_prevFlags)); ++i) {
        if (flags[i] != g_prevFlags[i] && len < 440)
            len += sprintf_s(line + len, sizeof(line) - len, " +%03X:%u>%u", 0x84 + i, g_prevFlags[i], flags[i]);
    }
    if (kDiag && len) Log("[%7lu ms] ctx=%p%s", GetTickCount() - g_t0, ctx, line);
    memcpy(g_prevFlags, flags, sizeof(g_prevFlags));
}

// --- Sonda odtwarzania animacji (tylko odczyt) -------------------------------------------
// RVA 0x37A040 (punkt "animation-submit" z DSROmniRoll): (ctx, out, animId?, ...). Logujemy
// wywolania z ID 800-999 oraz wszystkie przez 400 ms po wstrzyknietym skoku - zeby potwierdzic,
// ktory argument to ID animacji i ze skok to 900, zanim zaczniemy go podmieniac.
using PlayAnimFn = void*(__fastcall*)(void* ctx, void* out, int a3, int a4, char a5, int a6, int a7);
static PlayAnimFn g_origPlayAnim = nullptr;

// Ladowanie bez inputu: gra przerywa animacje akcji wywolaniem PlayAnim(ctx, out, -1, warstwa, 0,
// a6, 0) dla warstw 7 i 23 (podpatrzone w logu przy przerwaniu ladowania kierunkiem). Dla skokow
// 901/902 robimy to samo, jesli gra sama nie przerwala animacji do kLandingCancelMs.
constexpr DWORD kLandingCancelMs = 950;  // skok z ER: wybicie ~0.85 s (JT27 Ignore Gravity), potem ladowanie
static void* g_jumpAnimCtx = nullptr;   // ctx PlayAnim z momentu podmiany skoku
static int g_jumpAnimArg6 = 0;          // a6 z wywolania skoku (bity float -1.0)
static bool g_jumpEnded = true;         // gra (lub my) zakonczyla animacje skoku
static int g_layerLogLeft = 800;        // limit logu wywolan na warstwach innych niz 7/23
static bool g_drinkOnUpper = false;     // picie przeniesione na warstwy 5/17 jest aktywne
// Wylaczone: picie w ruchu robi teraz ESD z modu Simple Estus Walking (ChangeUpperBodyAnim na
// warstwie 5 + usuniete SwitchMotion). Przekierowanie zostawione jako referencja.
constexpr bool kDrinkUpperRedirect = false;

static void TrackDrink(int animId, int layer);  // nizej, wolny chod przy piciu
static void TrackItemBreak(int animId, int layer);  // below, DrinkSlowWalk section
static void TrackPlayerMainAnim(int animId, int layer);  // above InputDetour, free stamina

// Diagnostyka: kazda para (animacja, warstwa) logowana przy pierwszym uzyciu - do mapowania animacji
// ruchu (chod/bieg/sprint), ktore w DSR nie maja root motion i nie da sie ich rozpoznac z danych.
static void LogFirstUse(int anim, int layer) {
    static std::vector<long long> seen;
    long long key = (static_cast<long long>(anim) << 8) | (layer & 0xFF);
    for (long long k : seen) if (k == key) return;
    if (seen.size() > 2000) return;
    seen.push_back(key);
    Log("[%7lu ms] NOWA animacja %d warstwa %d", GetTickCount() - g_t0, anim, layer);
}

// --- Czasy atakow z ER (predkosc odtwarzania) ------------------------------------------------
// Animacja i TAE zostaja z DSR; odcinkami przyspieszamy odtwarzanie (ChrAnimData+0xA8, sciezka
// z DSR-Gadget: PlayerIns+0x48 -> +0x18 -> +0xA8), zeby trafienie i okno kolejnego ataku wypadly
// w czasach ER. Tabela: tools/gen_attack_speed_table.py. Czas animacji liczymy sami (dt * predkosc).
#include "attack_speed_table.h"
// TEST widocznosci: >0 = stala predkosc dla wszystkich atakow z tabeli (0 = predkosci z tabeli).
constexpr float kAttackSpeedTest = 0.0f;
static const AttackSpeedRow* g_atk = nullptr;
static float g_atkTime = 0.f;
static bool g_atkSpeedSet = false;

// Offset PlayerIns -> ChrMapData: DSR-Gadget podaje 0x48 (w tej wersji exe daje smieci), OmniRoll
// uzywa 0x68. Sprawdzamy kandydatow i bierzemy pierwszego z wiarygodna predkoscia (0.05..5).
static float* AnimSpeedPtrVia(int mapOff) {
    __try {
        auto base = reinterpret_cast<BYTE*>(GetModuleHandleA(nullptr));
        auto worldChr = *reinterpret_cast<BYTE**>(base + 0x1C77E50);
        auto player = worldChr ? *reinterpret_cast<BYTE**>(worldChr + 0x68) : nullptr;
        auto map = player ? *reinterpret_cast<BYTE**>(player + mapOff) : nullptr;
        if (reinterpret_cast<ULONG_PTR>(map) < 0x10000) return nullptr;
        auto anim = *reinterpret_cast<BYTE**>(map + 0x18);
        if (reinterpret_cast<ULONG_PTR>(anim) < 0x10000) return nullptr;
        float v = *reinterpret_cast<float*>(anim + 0xA8);
        if (!(v > 0.05f && v < 5.f)) return nullptr;
        return reinterpret_cast<float*>(anim + 0xA8);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return nullptr;
    }
}

static float* AnimSpeedPtr() {
    static int chosen = 0;
    if (chosen) return AnimSpeedPtrVia(chosen);
    for (int off : {0x68, 0x48, 0x28, 0x30, 0x38, 0x40, 0x50, 0x58, 0x60, 0x70}) {
        if (float* p = AnimSpeedPtrVia(off)) {
            chosen = off;
            Log("predkosc animacji: PlayerIns+0x%X -> +0x18 -> +0xA8 = %p (%.3f)", off, p, *p);
            return p;
        }
    }
    return nullptr;
}

static void SetAnimSpeed(float s) {
    float* p = AnimSpeedPtr();
    if (!p) return;
    __try { *p = s; } __except (EXCEPTION_EXECUTE_HANDLER) {}
}

static void AttackSpeedOnPlayAnim(int anim, int layer) {
    if (layer != 7) return;
    const AttackSpeedRow* row = nullptr;
    for (auto& r : kAttackSpeed) if (r.anim == anim) { row = &r; break; }
    if (!row && !g_atk) return;
    g_atk = row;
    g_atkTime = 0.f;
    if (!row && g_atkSpeedSet) { SetAnimSpeed(1.f); g_atkSpeedSet = false; }
}

static void AttackSpeedTick(float dt) {
    if (!g_atk) return;
    int seg = 0;
    while (seg < 3 && g_atkTime >= g_atk->knot[seg + 1]) ++seg;
    if (seg >= 3) {
        g_atk = nullptr;
        SetAnimSpeed(1.f);
        g_atkSpeedSet = false;
        return;
    }
    float s = kAttackSpeedTest > 0.f ? kAttackSpeedTest : g_atk->speed[seg];
    if (kDiag) {  // czy gra nadpisuje nasza wartosc miedzy klatkami
        static int lastSeg = -1;
        static const AttackSpeedRow* lastRow = nullptr;
        float* p = AnimSpeedPtr();
        float cur = -99.f;
        if (p) __try { cur = *p; } __except (EXCEPTION_EXECUTE_HANDLER) {}
        bool changed = seg != lastSeg || g_atk != lastRow || g_atkTime == 0.f;
        lastSeg = seg;
        lastRow = g_atk;
        if (changed)
            Log("[%7lu ms] predkosc: anim %d t=%.3f seg=%d ptr=%p przed=%.3f -> %.3f dt=%.4f", GetTickCount() - g_t0,
                g_atk->anim, g_atkTime, seg, p, cur, s, dt);
    }
    SetAnimSpeed(s);
    g_atkSpeedSet = true;
    g_atkTime += dt * s;
}

// --- Enemy attack probe (ER_DIAG only, read-only) ---------------------------------------------
// Boss tuning: distance and bearing between an enemy and the player while the enemy plays an attack
// (3000-3099 on layer 7), sampled every kEnemyProbeStepMs until the attack ends. Owner of a PlayAnim ctx
// = *(ctx+0x10) (FUN_14037A040 makes its virtual calls through it); position data as for the player:
// owner+0x68 -> +0x28 (+0x04 yaw, +0x10/+0x14/+0x18 X/Y/Z). Not verified for enemies before this probe:
// the player's own ctx is compared with ChrPosData() once and the result is logged.
// Bearing = angle from the enemy's facing to the player (0 = straight ahead); which side is positive is
// not established yet.
struct EnemyProbe { void* ctx; int anim; DWORD startAt, lastAt; float x0, z0; };
static EnemyProbe g_enemyProbe[4] = {};
constexpr DWORD kEnemyProbeStepMs = 100, kEnemyProbeMaxMs = 6000;

static BYTE* PosDataOfAnimCtx(void* ctx) {
    __try {
        auto owner = *reinterpret_cast<BYTE**>(static_cast<BYTE*>(ctx) + 0x10);
        if (reinterpret_cast<ULONG_PTR>(owner) < 0x10000) return nullptr;
        auto map = *reinterpret_cast<BYTE**>(owner + 0x68);
        if (reinterpret_cast<ULONG_PTR>(map) < 0x10000) return nullptr;
        auto pos = *reinterpret_cast<BYTE**>(map + 0x28);
        return reinterpret_cast<ULONG_PTR>(pos) < 0x10000 ? nullptr : pos;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return nullptr;
    }
}

static int PlayerHpForProbe() {
    __try {
        auto base = reinterpret_cast<BYTE*>(GetModuleHandleA(nullptr));
        auto worldChr = *reinterpret_cast<BYTE**>(base + 0x1C77E50);
        auto player = worldChr ? *reinterpret_cast<BYTE**>(worldChr + 0x68) : nullptr;
        return player ? *reinterpret_cast<int*>(player + 0x3E8) : -1;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return -1;
    }
}

// Returns false when the positions cannot be read (slot is then dropped by the caller).
static bool EnemyProbeLog(EnemyProbe& p, DWORD now, const char* tag) {
    BYTE* e = PosDataOfAnimCtx(p.ctx);
    BYTE* pl = ChrPosData();
    if (!e || !pl || e == pl) return false;
    float ex, ey, ez, yaw, px, py, pz;
    __try {
        yaw = *reinterpret_cast<float*>(e + 0x04);
        ex = *reinterpret_cast<float*>(e + 0x10); ey = *reinterpret_cast<float*>(e + 0x14); ez = *reinterpret_cast<float*>(e + 0x18);
        px = *reinterpret_cast<float*>(pl + 0x10); py = *reinterpret_cast<float*>(pl + 0x14); pz = *reinterpret_cast<float*>(pl + 0x18);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
    if (!_finite(yaw) || !_finite(ex) || !_finite(ey) || !_finite(ez) || fabsf(ex) > 1e5f || fabsf(ez) > 1e5f || fabsf(yaw) > 100.f)
        return false;
    if (p.lastAt == 0) { p.x0 = ex; p.z0 = ez; }
    float dx = px - ex, dz = pz - ez;
    float fx = -sinf(yaw), fz = -cosf(yaw);  // forward, same convention as the player (PLAN section 3)
    float bearing = atan2f(fx * dz - fz * dx, fx * dx + fz * dz) * 57.29578f;
    float moved = sqrtf((ex - p.x0) * (ex - p.x0) + (ez - p.z0) * (ez - p.z0));
    Log("[%7lu ms] enemy %p anim %d +%4lu ms%s: dist %.2f m, bearing %+.0f deg, moved %.2f m, dy %+.2f, yaw %.2f, player hp %d",
        now - g_t0, p.ctx, p.anim, now - p.startAt, tag, sqrtf(dx * dx + dz * dz), bearing, moved, py - ey, yaw,
        PlayerHpForProbe());
    p.lastAt = now ? now : 1;
    return true;
}

static void EnemyProbeOnPlayAnim(void* ctx, int anim, int layer) {
    if (layer != 7 || !ctx) return;
    if (ctx == g_playerAnimCtx || ctx == g_rollCtx) {
        static bool checked = false;
        if (!checked && ctx == g_playerAnimCtx && ChrPosData()) {
            checked = true;
            Log("[%7lu ms] enemy probe: player ctx+0x10 path %s ChrPosData()", GetTickCount() - g_t0,
                PosDataOfAnimCtx(ctx) == ChrPosData() ? "matches" : "DOES NOT match");
        }
        return;
    }
    DWORD now = GetTickCount();
    EnemyProbe* slot = nullptr;
    for (auto& p : g_enemyProbe) if (p.ctx == ctx) slot = &p;
    if (slot) {  // any new request on layer 7 (also -1) ends the tracked attack
        EnemyProbeLog(*slot, now, " END");
        slot->ctx = nullptr;
    }
    if (anim < 3000 || anim > 3099) return;
    if (!slot) for (auto& p : g_enemyProbe) if (!p.ctx) { slot = &p; break; }
    if (!slot) return;
    *slot = {ctx, anim, now, 0, 0.f, 0.f};
    if (!EnemyProbeLog(*slot, now, " START")) slot->ctx = nullptr;
}

static void EnemyProbeTick() {
    DWORD now = GetTickCount();
    for (auto& p : g_enemyProbe) {
        if (!p.ctx) continue;
        if (now - p.startAt > kEnemyProbeMaxMs) { p.ctx = nullptr; continue; }
        if (now - p.lastAt >= kEnemyProbeStepMs && !EnemyProbeLog(p, now, "")) p.ctx = nullptr;
    }
}

// --- Enemy target probe (ER_DIAG only, read-only) ----------------------------------------------
// Free sprint should end when an enemy aggroes (as in Elden Ring), not only after the first hit. There is
// no known "AI target" field. Hypothesis: enemies use the same ChrIns+0x1A0 the player uses for the lock-on
// target. The probe registers every non-player character seen in PlayAnim (owner = *(ctx+0x10)) and logs:
//  - changes of the enemy's +0x1A0 (qword) with the distance to the player ("target"),
//  - when the player locks on: which registered enemy holds that value in its first 0x100 bytes (handle offset),
//  - on an enemy's first attack (3000-3099, surely aggroed): dwords in +0x000..+0x5FF that went from zero to
//    non-zero or back since the character was first seen (idle) - candidates if +0x1A0 is not it.
struct TargetProbe { BYTE* chr; void* ctx; DWORD seenAt; ULONG64 target; bool attacked; DWORD idle[0x180]; };
static TargetProbe g_targetProbe[48] = {};

static void TargetProbeOnPlayAnim(void* ctx, int anim, int layer) {
    if (!ctx || ctx == g_playerAnimCtx || ctx == g_rollCtx) return;
    BYTE* chr = nullptr;
    __try { chr = *reinterpret_cast<BYTE**>(static_cast<BYTE*>(ctx) + 0x10); } __except (EXCEPTION_EXECUTE_HANDLER) { return; }
    if (reinterpret_cast<ULONG_PTR>(chr) < 0x10000) return;
    DWORD now = GetTickCount();
    TargetProbe* slot = nullptr;
    for (auto& t : g_targetProbe) if (t.chr == chr) { slot = &t; break; }
    if (!slot) {   // new character: take a free slot or the one not seen for the longest time
        slot = &g_targetProbe[0];
        for (auto& t : g_targetProbe) {
            if (!t.chr) { slot = &t; break; }
            if (now - t.seenAt > now - slot->seenAt) slot = &t;
        }
        slot->chr = chr; slot->ctx = ctx; slot->attacked = false; slot->target = 0;
        __try {
            memcpy(slot->idle, chr, sizeof(slot->idle));
            slot->target = *reinterpret_cast<ULONG64*>(chr + 0x1A0);
        } __except (EXCEPTION_EXECUTE_HANDLER) { slot->chr = nullptr; return; }
        Log("[%7lu ms] target probe: new chr %p (ctx %p, first anim %d L%d), +0x1A0 = %llX", now - g_t0, chr, ctx, anim,
            layer, slot->target);
    }
    slot->seenAt = now ? now : 1;
    if (layer != 7 || anim < 3000 || anim > 3099 || slot->attacked) return;
    slot->attacked = true;
    int n = 0;
    __try {
        const DWORD* cur = reinterpret_cast<const DWORD*>(chr);
        for (int i = 0; i < 0x180 && n < 40; i++) {
            if ((slot->idle[i] == 0) == (cur[i] == 0)) continue;
            Log("[%7lu ms] target probe: chr %p first attack %d, +0x%03X: idle %08lX -> %08lX", now - g_t0, chr, anim, i * 4,
                slot->idle[i], cur[i]);
            n++;
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) {
    }
}

static void TargetProbeTick(void* p3) {
    static DWORD lastAt = 0;
    static ULONG64 lastPlayerTarget = 0;
    DWORD now = GetTickCount();
    if (now - lastAt < 200) return;
    lastAt = now;
    BYTE* pl = ChrPosData();
    __try {
        BYTE* me = *reinterpret_cast<BYTE**>(static_cast<BYTE*>(p3) + 0x10);
        if (reinterpret_cast<ULONG_PTR>(me) < 0x10000) return;
        ULONG64 mine = *reinterpret_cast<ULONG64*>(me + 0x1A0);
        if (mine != lastPlayerTarget) {
            Log("[%7lu ms] target probe: player +0x1A0 %llX -> %llX (player chr %p)", now - g_t0, lastPlayerTarget, mine, me);
            lastPlayerTarget = mine;
            DWORD lo = static_cast<DWORD>(mine);
            for (auto& t : g_targetProbe) {
                if (!t.chr || !lo) continue;
                const DWORD* d = reinterpret_cast<const DWORD*>(t.chr);
                for (int i = 0; i < 0x40; i++)
                    if (d[i] == lo) Log("[%7lu ms] target probe:   locked value found in chr %p at +0x%02X", now - g_t0, t.chr, i * 4);
                if (reinterpret_cast<ULONG64>(t.chr) == mine) Log("[%7lu ms] target probe:   locked value = chr %p itself", now - g_t0, t.chr);
            }
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return;
    }
    for (auto& t : g_targetProbe) {
        if (!t.chr || now - t.seenAt > 120000) continue;
        ULONG64 v;
        __try { v = *reinterpret_cast<ULONG64*>(t.chr + 0x1A0); } __except (EXCEPTION_EXECUTE_HANDLER) { t.chr = nullptr; continue; }
        if (v == t.target) continue;
        float dist = -1.f;
        BYTE* e = PosDataOfAnimCtx(t.ctx);
        if (e && pl) __try {
            float dx = *reinterpret_cast<float*>(pl + 0x10) - *reinterpret_cast<float*>(e + 0x10);
            float dz = *reinterpret_cast<float*>(pl + 0x18) - *reinterpret_cast<float*>(e + 0x18);
            dist = sqrtf(dx * dx + dz * dz);
        } __except (EXCEPTION_EXECUTE_HANDLER) {
        }
        Log("[%7lu ms] target probe: chr %p +0x1A0 %llX -> %llX, dist %.1f m", now - g_t0, t.chr, t.target, v, dist);
        t.target = v;
    }
}

// A hit while drinking: the patched ESD plays the item animation on the upper body (layers 6 / 18) and the
// game's damage reaction (2000-2099 on layers 11 / 26) does not end it - a knockdown then ran for 3 s with
// the torso still held by the drink pose (log 2026-11-13: 2026 at 175.06 s, layer 6 released at 178.02 s).
// Vanilla drinks on the full body, where the reaction replaces it. Here the item animation is ended by
// hand as soon as the reaction starts.
static int g_itemUpperAnim = -1;  // item animation the player currently has on layer 6
static int g_playerDmgAnim = -1;  // player's current layer-11 animation (hit reaction), for the hang probe
static void ItemUpperOnPlayAnim(void* ctx, void* out, int anim, int layer, char a5, int a6) {
    if (!g_playerAnimCtx || ctx != g_playerAnimCtx) return;
    if (layer == 6) { g_itemUpperAnim = IsItemWalkAnim(anim) ? anim : -1; return; }
    if (layer == 11) g_playerDmgAnim = anim;
    if (layer != 11 || anim < 2000 || anim > 2099 || g_itemUpperAnim < 0 || !g_itemHitCancelOn) return;
    Log("[%7lu ms] item: hit reaction %d during item anim %d - ending the upper-body animation",
        GetTickCount() - g_t0, anim, g_itemUpperAnim);
    g_itemUpperAnim = -1;
    DWORD now = GetTickCount();
    g_itemBrokenAt = now ? now : 1;  // slow walk off (DrinkActive)
    g_origPlayAnim(ctx, out, -1, 6, a5, a6, 1);
    g_origPlayAnim(ctx, out, -1, 18, a5, a6, 0);
}

static void* __fastcall PlayAnimDetour(void* ctx, void* out, int a3, int a4, char a5, int a6, int a7) {
    if (kDiag && a3 >= 0) LogFirstUse(a3, a4);
    if (kDiag) { EnemyProbeOnPlayAnim(ctx, a3, a4); TargetProbeOnPlayAnim(ctx, a3, a4); }
    ItemUpperOnPlayAnim(ctx, out, a3, a4, a5, a6);
    // Diagnostyka: kazde zlecenie na warstwie glownej (takze koniec animacji, a3 = -1), z ctx - gracz ma ten sam ctx co skok.
    if (kDiag && (a4 == 7 || a4 == 23))
        Log("[%7lu ms] L%d ctx=%p anim=%d a5=%d a6=%d a7=%d%s", GetTickCount() - g_t0, a4, ctx, a3, a5, a6, a7,
            (ctx == g_playerAnimCtx || ctx == g_rollCtx) ? " (gracz)" : "");
    a3 = AirAttackSubstitute(ctx, a3, a4, a6);
    OmniRollOnPlayAnim(ctx, a3, a4, a6);
    AttackSpeedOnPlayAnim(a3, a4);
    // Pomiar spadania/ladowania: skok 900-999 i podejrzane spadanie/ladowanie DSR 1500-1699, kazda warstwa.
    if (kDiag && ((a3 >= 900 && a3 < 1000) || (a3 >= 1500 && a3 < 1700)))
        Log("[%7lu ms] SPADEK anim %d warstwa %d", GetTickCount() - g_t0, a3, a4);
    // Pomiar atakow: kazde zlecenie animacji ataku (grupa broni 20-49, ID 3000-5999) na warstwie glownej.
    if (kDiag && a4 == 7 && a3 >= 200000 && a3 < 500000 && a3 % 10000 >= 3000 && a3 % 10000 < 6000)
        Log("[%7lu ms] ATAK %d", GetTickCount() - g_t0, a3);
    TrackDrink(a3, a4);
    if (ctx == g_playerAnimCtx || ctx == g_rollCtx) { TrackItemBreak(a3, a4); TrackPlayerMainAnim(a3, a4); }
    DWORD sinceJump = g_lastJumpInject ? GetTickCount() - g_lastJumpInject : ~0ul;
    bool afterJump = sinceJump < 400;
    if (a3 == -1 && ctx == g_jumpAnimCtx) g_jumpEnded = true;
    if (afterJump && a3 == kJumpAnimVanilla && g_jumpVariant != kJumpAnimVanilla) {
        g_jumpAnimCtx = ctx;
        g_jumpAnimArg6 = a6;
        g_jumpEnded = false;
        Log("[%7lu ms] skok: animacja %d -> %d (warstwa %d)", GetTickCount() - g_t0, a3, g_jumpVariant, a4);
        a3 = g_jumpVariant;
    } else if (kDrinkUpperRedirect && a3 >= 7585 && a3 <= 7587 && (a4 == 7 || a4 == 23)) {
        // EKSPERYMENT estus na gornej czesci ciala: warstwy 7/23 (cale cialo) -> 5/17 (gorna czesc
        // ciala, jak blok w marszu: warstwa 5 z a7=2, warstwa 17 z a7=0 - wzorzec z logu tarczy).
        int upper = a4 == 7 ? 5 : 17;
        g_drinkOnUpper = true;
        Log("[%7lu ms] estus: anim %d warstwa %d -> %d (eksperyment gorna czesc ciala)", GetTickCount() - g_t0, a3, a4, upper);
        return g_origPlayAnim(ctx, out, a3, upper, a5, a6, upper == 5 ? 2 : 0);
    } else if (a3 == -1 && g_drinkOnUpper && (a4 == 7 || a4 == 23)) {
        // Gra konczy czesc picia na 7/23 - konczymy tez nasza kopie na 5/17.
        int upper = a4 == 7 ? 5 : 17;
        g_origPlayAnim(ctx, out, -1, upper, a5, a6, upper == 5 ? 2 : 0);
        if (a4 == 23) g_drinkOnUpper = false;  // kolejna czesc picia ustawi flage ponownie
    } else if (kDiag && a4 != 7 && a4 != 23 && g_layerLogLeft-- > 0) {
        // Warstwy inne niz glowne 7/23 - szukamy, jak gra odtwarza animacje gornej czesci ciala
        // (tarcza w marszu). Limit 800 wpisow.
        Log("[%7lu ms] PlayAnim warstwa %d: a3=%d a5=%d a6=%d a7=%d", GetTickCount() - g_t0, a4, a3, a5, a6, a7);
    } else if (kDiag && g_lastItemReq && GetTickCount() - g_lastItemReq < 3000) {
        Log("[%7lu ms] PlayAnim item +%4lums ctx=%p a3=%d a4=%d a5=%d a6=%d a7=%d", GetTickCount() - g_t0,
            GetTickCount() - g_lastItemReq, ctx, a3, a4, a5, a6, a7);
    } else if (kDiag && (sinceJump < 1500 || (a3 >= 800 && a3 < 1000))) {
        // 1.5 s po skoku: wszystkie wywolania - zeby zobaczyc, czym gra przerywa ladowanie.
        Log("[%7lu ms] PlayAnim +%4lums ctx=%p a3=%d a4=%d a5=%d a6=%d a7=%d", GetTickCount() - g_t0,
            sinceJump, ctx, a3, a4, a5, a6, a7);
    }
    if (a4 == 7 && (a3 == 900 || a3 == 901 || a3 == 902)) { g_momCtx = ctx; g_momA6 = a6; }
    AirControlOnPlayAnim(a3, a4);
    void* ret = g_origPlayAnim(ctx, out, a3, a4, a5, a6, a7);
    AirAttackAfterPlayAnim(a3, a4);
    return ret;
}

// --- Sterowanie w locie (jak w ER) ----------------------------------------------------------
// Skok DSR to animacja z ruchem w srodku - bez sterowania. W TAE skokow zdjeta blokada obrotu
// (postac obraca sie do galki), a tu dosuwamy pozycje w kierunku patrzenia proporcjonalnie do
// wychylenia galki, od oderwania (~0.33 s) do konca skoku. Pozycja: PlayerIns+0x68 -> +0x28 (ChrPosData,
// DSR-Gadget): +0x4 kat, +0x10/+0x18 X/Z.
constexpr DWORD kAirFromMs = 330, kAirToMs = 950;
constexpr float kAirDriftStand = 2.0f;  // m/s, skok z miejsca (animacja bez ruchu poziomego)
constexpr float kAirDriftMoving = 0.8f; // m/s, skoki w ruchu (animacja juz niesie do przodu)
static DWORD g_airJumpAt = 0;
static float g_airY0 = 0.f;            // wysokosc w chwili skoku
static bool g_jumpLanded = false;       // wykryte ladowanie (konczy skok bez czekania na kLandingCancelMs)
constexpr DWORD kLandCheckFromMs = 500;
static float g_airDrift = 0.f;
static BYTE* ChrPosData() {
    __try {
        auto base = reinterpret_cast<BYTE*>(GetModuleHandleA(nullptr));
        auto worldChr = *reinterpret_cast<BYTE**>(base + 0x1C77E50);
        auto player = worldChr ? *reinterpret_cast<BYTE**>(worldChr + 0x68) : nullptr;
        auto map = player ? *reinterpret_cast<BYTE**>(player + 0x68) : nullptr;
        auto pos = map ? *reinterpret_cast<BYTE**>(map + 0x28) : nullptr;
        return reinterpret_cast<ULONG_PTR>(pos) < 0x10000 ? nullptr : pos;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return nullptr;
    }
}

// Przysiad przy wybiciu: w ER root schodzi ~0.3 m w dol; w DSR ziemia blokuje i model wisi nad
// podlozem. Na czas przysiadu wylaczamy kolizje z mapa (ChrMapData+0x104, bit 0x10 DisableMapHit,
// DSR-Gadget); grawitacja jest wtedy wylaczona przez JT27 w TAE skoku.
constexpr DWORD kDipEndMs = 350;
static bool g_mapHitOff = false;

static void SetMapHit(bool enabled) {
    __try {
        auto base = reinterpret_cast<BYTE*>(GetModuleHandleA(nullptr));
        auto worldChr = *reinterpret_cast<BYTE**>(base + 0x1C77E50);
        auto player = worldChr ? *reinterpret_cast<BYTE**>(worldChr + 0x68) : nullptr;
        auto map = player ? *reinterpret_cast<BYTE**>(player + 0x68) : nullptr;
        if (reinterpret_cast<ULONG_PTR>(map) < 0x10000) return;
        auto flags = reinterpret_cast<DWORD*>(map + 0x104);
        if (enabled) *flags &= ~0x10u; else *flags |= 0x10u;
        g_mapHitOff = !enabled;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
    }
}

static void AirControlOnPlayAnim(int anim, int layer) {
    if (layer != 7) return;
    if (anim == 900 || anim == 901 || anim == 902) {
        g_airJumpAt = GetTickCount();
        g_physProbeAt = g_airJumpAt;
        g_airDrift = anim == 901 ? kAirDriftStand : kAirDriftMoving;
        g_jumpLanded = false;
        AirMomentumStart(anim);
        if (BYTE* p = ChrPosData()) __try { g_airY0 = *reinterpret_cast<float*>(p + 0x14); } __except (EXCEPTION_EXECUTE_HANDLER) {}
        SetMapHit(false);
    } else {
        AirMomentumOnOtherAnim();  // koniec animacji skoku albo inna akcja (atak z wyskoku)
        if (anim >= 0) {
            g_airJumpAt = 0;
            if (g_mapHitOff) SetMapHit(true);
        }
    }
}

// --- Ataki z wyskoku (ER) ----------------------------------------------------------------------
// W skokach 900-902 okno ataku prawa reka jest otwarte od 0.25 s, a klawisz przyjmowany od poczatku
// skoku (tools/open_air_attack.py), wiec gra sama wybiera atak broni. W locie podmieniamy go na zamach
// z ER (tools/add_jump_attacks.py): R1 / atak z biegu -> GG3700 (1H) / GG4700 (2H), R2 -> GG3710 /
// GG4710. Warstwa 23 dostaje to samo co warstwa 7 (to samo zlecenie, chwile pozniej).
// v2 (2026-11-12), jak w ER:
//   - zamach nie ma wlasnego ruchu: od chwili ataku postac leci balistycznie (AirMomentumTick) z
//     wektorem z ostatniej klatki skoku; pion ograniczony tak, zeby szczyt wypadl jak w zwyklym skoku;
//   - w chwili ladowania zamach przechodzi w animacje ladowania z ER (ten sam ruch na ziemi +
//     wstawanie, okna przerwan w czasach ER) i jest przewijany do czasu, w ktorym byl zamach:
//     ladowanie przed trafieniem -> wersja z trafieniem, po trafieniu -> wersja bez trafienia;
//   - zamach skonczony w powietrzu (dlugi upadek) -> koniec animacji, dalej zwykle spadanie gry.
constexpr DWORD kAirAttackFromMs = 230, kAirAttackToMs = 1100;
constexpr float kJumpApex = 1.16f;        // szczyt skoku nad poziomem startu [m] (root motion 900/902)
constexpr float kAirAtkGravity = 16.0f;   // m/s^2 w ataku z wyskoku (luk animacji skoku jest ostrzejszy niz 9.8)
// Landing sync: the landing animation is advanced to the swing time in ONE frame by a one-frame speed
// spike (v2.3 used 4.5x over ~150 ms, which showed the weapon snapping back to the start pose and
// whipping forward - reported as a flicker on touchdown). AnimSpeedPtrVia rejects values >= 5, so the
// spike is written and restored through a cached pointer (AirAttackSpeed).
constexpr float kLandSyncSpeed = 90.0f;   // upper bound of the one-frame spike
constexpr bool kLandSync = true;          // false = ladowanie zawsze od poczatku animacji
// Wczesny atak (postac < ~0.5 m nad ziemia): silnik po wlaczeniu grawitacji uznaje ja za stojaca, gasi
// +0x1F3 i zeruje predkosc (log 2026-11-12: atak w 250 ms, wysokosc 0.31 m -> 'ladowanie' po 15 ms).
// Przez ten czas od przejecia lotu trzymamy +0x1F3 = 1, dopoki postac nie oderwie sie od ziemi.
constexpr DWORD kAirAtkLiftMs = 250;
// Rozped poziomy po ataku: czesc predkosci skoku i bez dodatku za galke (test 2026-11-12: 'postac jest
// pchana do przodu' - 7.6-7.8 m/s trzymane do ladowania; zwykly skok ze sprintu ma srednio ~6.5 i hamuje).
constexpr float kAirAtkHoriz = 0.85f;
static int g_airSubFrom = -1, g_airSubTo = -1;
static DWORD g_airSubAt = 0;
#include "jump_attack_table.h"  // tools/add_jump_attacks.py
enum { kAtkNone, kAtkAir, kAtkLand };
static int g_airAtkState = kAtkNone;
static const JumpAttackRow* g_airAtkRow = nullptr;
static DWORD g_airAtkAt = 0;              // start zamachu
static DWORD g_airAtkLandAt = 0;          // start ladowania
static float g_airAtkLandT0 = 0.f;        // czas animacji ladowania, do ktorego przewijamy [s]
static float g_airAtkFfLeft = 0.f;        // ile jeszcze przewinac [s]
static bool g_airAtkSpeedSet = false, g_airAtkSeenAir = false;
static void* g_airAtkCtx = nullptr;
static int g_airAtkA6 = 0;
static float g_jumpV[3] = {};             // predkosc proxy z ostatniej klatki animacji skoku (AirMomentumTick)
static bool g_jumpVOk = false;
static float g_airAtkV[3] = {};           // wektor przejmowany przez AirMomentumTick po ataku
static bool g_airAtkVOk = false;
static DWORD g_airAtkVAt = 0;

// Ladowanie (v2.3). Test 2026-11-12: gra sama konczy atak w skoku w chwili ladowania (-1 na warstwach 7
// i 23, w tej samej klatce co nasze zlecenie albo klatke pozniej) - nasze ladowanie bylo od razu kasowane
// i postac mogla biec natychmiast. Dlatego: (1) ladowanie zlecamy ponownie zaraz po tym -1 gry,
// (2) ESD jest wtedy juz w stanie spoczynku i okna przerwan z TAE nic nie znacza, wiec recovery pilnuje
// DLL: osie ruchu = 0 do landMoveMs, flagi atakow do landAtkMs, unik do polowy miedzy nimi (czasy ER).
static int g_airAtkLandAnim = 0;
static bool g_airAtkReplay = false;
static int g_airAtkReplays = 0;           // how many times the landing animation was (re)started
static DWORD g_airAtkTouchAt = 0;         // touchdown time (does not move on replays)
static float g_airAtkLastPos[3] = {};     // X/Z/Y from the previous tick while landing
static bool g_airAtkLastPosOk = false;
// Log 2026-11-12 (v2.4): one frame after the landing animation started the character moved ~0.9 m in a
// single frame (52 m/s). Any per-frame step above this during the first kLandJumpGuardMs is undone.
constexpr float kLandJumpMaxStep = 0.25f;
constexpr DWORD kLandJumpGuardMs = 400;
static DWORD g_airAtkReplayAt = 0;
static int g_lastBaseGroup = 0;           // ostatnia zwykla grupa broni gracza (20-49) widziana na warstwie 7

static float* g_airAtkSpeedPtr = nullptr;
static float g_airAtkDt = 1.f / 60.f;     // last frame time seen by AirAttackTick
static int g_airAtkSpikeTicks = 1;        // ticks until the time-jump speed is restored
static void AirAttackSpeed(float s) {
    if (float* p = AnimSpeedPtr()) g_airAtkSpeedPtr = p;  // only resolvable while the current value is sane
    if (!g_airAtkSpeedPtr) return;
    __try { *g_airAtkSpeedPtr = s; } __except (EXCEPTION_EXECUTE_HANDLER) {}
}

// Root motion hold for the time-jump frame. FUN_1402bbe40: with +0x1F3 set the velocity is taken from
// +0xD0 (previous frame) instead of the animation's root motion. We set +0x1F3 and zero +0xD0 and the
// proxy velocity for the frame in which the animation is advanced, then clear the flag again.
static void AirAttackRootHold(bool on) {
    BYTE* ph = ChrPosData();
    if (!ph) return;
    __try {
        ph[0x1F3] = on ? 1 : 0;
        if (!on) return;
        for (int off : {0xD0, 0xD4, 0xD8}) *reinterpret_cast<float*>(ph + off) = 0.f;
        auto proxy = *reinterpret_cast<BYTE**>(ph + 0x38);
        if (reinterpret_cast<ULONG_PTR>(proxy) >= 0x10000)
            for (int off : {0x60, 0x64, 0x68}) *reinterpret_cast<float*>(proxy + off) = 0.f;
    } __except (EXCEPTION_EXECUTE_HANDLER) {}
}

static void AirAttackReset() {
    if (g_airAtkSpeedSet) { AirAttackSpeed(1.f); g_airAtkSpeedSet = false; }
    g_airAtkState = kAtkNone;
    g_airAtkFfLeft = 0.f;
    g_airAtkMoveLock = false;
    g_airAtkReplay = false;
}

static void AirAttackPlay(int anim) {  // jak gra: najpierw koniec na 7/23, potem nowa animacja
    unsigned long long out[2] = {};
    for (int layer : {7, 23}) g_origPlayAnim(g_airAtkCtx, out, -1, layer, 0, g_airAtkA6, 0);
    if (anim > 0)
        for (int layer : {7, 23}) g_origPlayAnim(g_airAtkCtx, out, anim, layer, 0, g_airAtkA6, 0);
}

static float AirAttackLandMs() { return g_airAtkLandT0 * 1000.f + static_cast<float>(GetTickCount() - g_airAtkLandAt); }

static bool AirAttackOnGround() {
    BYTE* ph = ChrPosData();
    if (!ph) return false;
    __try { return ph[0x32] && !ph[0x1F2] && !ph[0x1F4]; } __except (EXCEPTION_EXECUTE_HANDLER) { return false; }
}

// t = czas zamachu [ms]. playNow = zlecamy od razu (ladowanie wykryl nasz tick); false = czekamy, az gra
// skonczy swoje -1 na warstwie 23 (AirAttackAfterPlayAnim).
static void AirAttackReplayNow(bool fromGame = false);

static void AirAttackBeginLand(DWORD t, bool playNow) {
    DWORD now = GetTickCount();
    const JumpAttackRow* r = g_airAtkRow;
    bool beforeHit = t + 20 < r->hitMs;
    int land = t >= r->swingEndMs ? 0 : beforeHit ? r->landHit : r->landFollow;
    Log("[%7lu ms] jump attack: touchdown after %lu ms of swing (hit from %u ms, seen by %s) -> %d, attack from %u ms, move from %u ms",
        now - g_t0, t, r->hitMs, playNow ? "DLL tick" : "game -1", land, r->landAtkMs, r->landMoveMs);
    if (!land) {
        if (playNow) AirAttackPlay(-1);
        AirAttackReset();
        return;
    }
    g_airAtkState = kAtkLand;
    g_airAtkLandAnim = land;
    g_airAtkLandAt = now;
    g_airAtkLandT0 = kLandSync ? t / 1000.f : 0.f;
    g_airAtkFfLeft = g_airAtkLandT0;
    g_airAtkMoveLock = true;
    g_airAtkReplays = 0;
    g_airAtkTouchAt = now;
    g_airAtkLastPosOk = false;
    g_airAtkReplay = !playNow;  // game -1 already seen on layer 7: start after its -1 on layer 23
    g_airAtkReplayAt = now;
    if (playNow) AirAttackReplayNow();  // the game answers with -1 on 7/23, then the landing restarts once
}

static void AirAttackReplayNow(bool fromGame) {  // gra skasowala nasze ladowanie swoim -1 - zlecamy je jeszcze raz
    DWORD now = GetTickCount();
    g_airAtkReplay = false;
    ++g_airAtkReplays;
    if (g_airAtkSpeedSet) { AirAttackSpeed(1.f); g_airAtkSpeedSet = false; }
    AirAttackPlay(g_airAtkLandAnim);
    if (kLandSync) g_airAtkLandT0 += (now - g_airAtkLandAt) / 1000.f;
    g_airAtkLandAt = now;
    // Arm the time jump right here. Frame order seen in the logs: input tick -> game state machine (its
    // -1 and this restart) -> animation update -> physics, so the next animation update is the first one
    // of the landing animation; the following tick restores the speed.
    g_airAtkFfLeft = 0.f;
    if (g_airAtkLandT0 > 0.01f) {
        float s = 1.f + g_airAtkLandT0 / g_airAtkDt;
        if (s > kLandSyncSpeed) s = kLandSyncSpeed;
        AirAttackSpeed(s);
        g_airAtkSpeedSet = true;
        AirAttackRootHold(true);
        // Armed from the game's -1 (after this frame's tick): the animation update that advances the
        // restarted animation comes after the NEXT tick, so the spike must survive one tick.
        g_airAtkSpikeTicks = fromGame ? 2 : 1;
    }
    Log("[%7lu ms] jump attack: landing %d started (#%d, %lu ms after touchdown, animation time %.2f s)", now - g_t0, g_airAtkLandAnim,
        g_airAtkReplays, now - g_airAtkTouchAt, g_airAtkLandT0);
}

static void AirAttackAfterPlayAnim(int anim, int layer) {
    if (g_airAtkReplay && layer == 23 && anim == -1 && g_airAtkState == kAtkLand && g_origPlayAnim) AirAttackReplayNow(true);
}

static void AirAttackTick(float dt) {
    if (dt > 0.001f && dt < 0.1f) g_airAtkDt = dt;
    if (g_airAtkState == kAtkNone || !g_origPlayAnim || !g_airAtkRow) return;
    DWORD now = GetTickCount();
    if (g_airAtkState == kAtkLand) {
        if (g_airAtkReplay && now - g_airAtkReplayAt > 60) AirAttackReplayNow();  // -1 na warstwie 23 nie przyszlo
        if (BYTE* pos = ChrPosData()) __try {  // undo a one-frame forward jump right after touchdown
            float* x = reinterpret_cast<float*>(pos + 0x10);
            float* z = reinterpret_cast<float*>(pos + 0x18);
            if (g_airAtkLastPosOk && now - g_airAtkTouchAt < kLandJumpGuardMs) {
                float dx = *x - g_airAtkLastPos[0], dz = *z - g_airAtkLastPos[1];
                if (dx * dx + dz * dz > kLandJumpMaxStep * kLandJumpMaxStep) {
                    Log("[%7lu ms] jump attack: undone a %.2f m one-frame step %lu ms after touchdown", now - g_t0,
                        sqrtf(dx * dx + dz * dz), now - g_airAtkTouchAt);
                    *x = g_airAtkLastPos[0];
                    *z = g_airAtkLastPos[1];
                    *reinterpret_cast<float*>(pos + 0x14) = g_airAtkLastPos[2];
                }
            }
            g_airAtkLastPos[0] = *x;
            g_airAtkLastPos[1] = *z;
            g_airAtkLastPos[2] = *reinterpret_cast<float*>(pos + 0x14);
            g_airAtkLastPosOk = true;
        } __except (EXCEPTION_EXECUTE_HANDLER) {}
        if (g_airAtkReplay) return;  // landing animation not started yet (waiting for the game's own -1)
        if (g_airAtkSpeedSet && --g_airAtkSpikeTicks > 0) {
            AirAttackRootHold(true);  // keep ignoring root motion until the jump has been applied
            return;
        }
        if (g_airAtkSpeedSet) {
            AirAttackSpeed(1.f);
            g_airAtkSpeedSet = false;
            AirAttackRootHold(false);
        } else if (g_airAtkFfLeft > 0.01f) {  // jump to the swing time in one frame
            float step = dt > 0.001f ? dt : 0.0167f;
            float s = 1.f + g_airAtkFfLeft / step;
            if (s > kLandSyncSpeed) s = kLandSyncSpeed;
            AirAttackSpeed(s);
            g_airAtkSpeedSet = true;
            g_airAtkSpikeTicks = 1;
            g_airAtkFfLeft = 0.f;
            AirAttackRootHold(true);
            return;
        }
        float ms = AirAttackLandMs();
        g_airAtkMoveLock = ms < g_airAtkRow->landMoveMs;
        float mag = sqrtf(g_axis[0] * g_axis[0] + g_axis[1] * g_axis[1]);
        if (!g_airAtkMoveLock && mag > 0.3f) {  // okno ruchu otwarte i gracz chce isc - konczymy ladowanie
            AirAttackPlay(-1);
            Log("[%7lu ms] atak z wyskoku: ladowanie przerwane ruchem po %.2f s animacji", now - g_t0, ms / 1000.f);
            AirAttackReset();
            return;
        }
        // Bez inputu: koniec, gdy w ER animacja przechodzi juz w postawe (dalej tylko dociaganie pozy).
        if (ms >= g_airAtkRow->landEndMs) {
            AirAttackPlay(-1);
            Log("[%7lu ms] atak z wyskoku: koniec ladowania bez inputu (%.2f s animacji)", now - g_t0, ms / 1000.f);
            AirAttackReset();
        }
        return;
    }
    DWORD t = now - g_airAtkAt;
    if (t > 6000) { AirAttackReset(); return; }
    BYTE* ph = ChrPosData();
    if (!ph) return;
    bool ground = false, f3 = false, gravOff = true;
    __try { ground = ph[0x32] != 0; f3 = ph[0x1F3] != 0; gravOff = ph[0x1F2] || ph[0x1F4]; } __except (EXCEPTION_EXECUTE_HANDLER) { return; }
    if (!ground) g_airAtkSeenAir = true;
    bool landed = ground && !f3 && !gravOff && t >= 50 && (g_airAtkSeenAir || t > kAirAtkLiftMs + 100);
    if (!landed) {
        if (t >= g_airAtkRow->swingEndMs) {  // zamach skonczony w powietrzu - dalej zwykle spadanie
            AirAttackPlay(-1);
            Log("[%7lu ms] atak z wyskoku: zamach skonczony w powietrzu po %lu ms", now - g_t0, t);
            AirAttackReset();
        }
        return;
    }
    AirAttackBeginLand(t, true);  // start the landing in this tick (v2.4-v2.7 passed false: 60 ms of waiting)
}

static int AirAttackSubstitute(void* ctx, int anim, int layer, int a6) {
    // Kazde zlecenie gry na warstwie 7 (inna akcja, trafienie, koniec animacji) konczy nasz stan;
    // nasze wlasne zlecenia ida przez g_origPlayAnim i tu nie trafiaja.
    if (layer == 7 && g_airAtkState != kAtkNone) {
        DWORD now = GetTickCount();
        // Gra konczy atak w skoku w chwili ladowania (-1 na 7, potem na 23) - wtedy wchodzi nasze ladowanie.
        if (anim == -1 && g_airAtkState == kAtkAir && g_airAtkSeenAir && now - g_airAtkAt >= 100 && AirAttackOnGround()) {
            AirAttackBeginLand(now - g_airAtkAt, false);
            return anim;
        }
        if (anim == -1 && g_airAtkState == kAtkLand && g_airAtkReplays < 3 && now - g_airAtkTouchAt < 250) {
            g_airAtkReplay = true;
            g_airAtkReplayAt = now;
            return anim;
        }
        AirAttackReset();
    }
    // Grupy broni 20-49 oraz grupy specjalne 120-149 (np. R2 topora gargulca = 1254300).
    bool weapon = (anim >= 200000 && anim < 500000) || (anim >= 1200000 && anim < 1500000);
    if (!weapon || (layer != 7 && layer != 23)) return anim;
    if (layer == 7 && anim < 500000 && ctx == g_momCtx) g_lastBaseGroup = anim / 10000;  // zwykla grupa broni gracza
    if (layer == 23 && anim == g_airSubFrom && GetTickCount() - g_airSubAt < 100) return g_airSubTo;
    if (layer != 7 || !g_airJumpAt) return anim;
    DWORD t = GetTickCount() - g_airJumpAt;
    if (t < kAirAttackFromMs || t > kAirAttackToMs) return anim;
    int group = anim / 10000, id = anim % 10000, to = 0;
    switch (id) {
        // 3900 / 4900: wlasny atak DSR w skoku (R1) - to jego gra zleca najczesciej (log 2026-11-12).
        case 3000: case 3001: case 3002: case 3500: case 3900: to = 3700; break;
        case 4000: case 4001: case 4002: case 4500: case 4900: to = 4700; break;
        case 3300: case 3310: to = 3710; break;
        case 4300: case 4310: to = 4710; break;
        default: return anim;
    }
    // Wiersz tabeli: wlasna grupa; dla grupy specjalnej - ostatnia zwykla grupa gracza, potem grupa % 100.
    const JumpAttackRow* row = nullptr;
    for (int g : {group, group >= 100 ? g_lastBaseGroup : 0, group >= 100 ? group % 100 : 0}) {
        if (!g) continue;
        for (auto& r : kJumpAttacks) if (r.anim == g * 10000 + to) { row = &r; break; }
        if (row) break;
    }
    if (!row) return anim;  // brak animacji ER dla tej broni - zwykly atak DSR
    g_airSubFrom = anim;
    g_airSubTo = row->anim;
    g_airSubAt = GetTickCount();
    g_airAtkCtx = ctx;
    g_airAtkA6 = a6;
    g_airAtkRow = row;
    g_airAtkAt = g_airSubAt;
    g_airAtkSeenAir = false;
    g_airAtkState = kAtkAir;
    // Wektor lotu z ostatniej klatki skoku; pion najwyzej taki, zeby dolecial do szczytu zwyklego skoku.
    g_airAtkVOk = false;
    float h = 0.f;
    if (g_jumpVOk) {
        if (BYTE* p = ChrPosData()) __try { h = *reinterpret_cast<float*>(p + 0x14) - g_airY0; } __except (EXCEPTION_EXECUTE_HANDLER) {}
        float room = kJumpApex - h;
        float cap = sqrtf(2.f * kAirAtkGravity * (room > 0.02f ? room : 0.02f));
        g_airAtkV[0] = g_jumpV[0];
        g_airAtkV[1] = g_jumpV[1] < cap ? g_jumpV[1] : cap;
        g_airAtkV[2] = g_jumpV[2];
        g_airAtkVAt = g_airSubAt;
        g_airAtkVOk = true;
    }
    Log("[%7lu ms] atak z wyskoku: %d -> %d po %lu ms skoku, wysokosc %.2f, predkosc skoku %.2f %.2f %.2f -> pion %.2f%s",
        GetTickCount() - g_t0, anim, g_airSubTo, t, h, g_jumpV[0], g_jumpV[1], g_jumpV[2], g_airAtkV[1], g_airAtkVOk ? "" : " (brak probki)");
    return g_airSubTo;
}

// Bufor klikniecia ataku w skoku. Gra reaguje tylko na wcisniecie, ktore wypadnie w oknie przerwania
// atakiem (od 0.25 s skoku) - klik zaraz po skoku przepadal i trzeba bylo spamowac (test 2026-11-12).
// Flagi handlera wejscia (z logu zmian ctx przy klikach): +0x84 i +0x8B = R1 trzymany (lewy przycisk
// myszy, daje atak 3900), +0x89 = R2 trzymany (daje 3300/4300), +0x1C4 bit 0 = jest jakas akcja. Klik sprzed okna odtwarzamy po otwarciu okna: flaga na
// 1 przez kilka klatek; gdy przycisk jest nadal trzymany, jedna klatka z 0 robi nowe wcisniecie.
constexpr DWORD kAtkBufOpenMs = 255, kAtkBufCloseMs = 310;
constexpr bool kAtkBuffer = true;
static void AirAttackBuffer(BYTE* ctx) {
    static BYTE prev1 = 0, prev2 = 0;
    static DWORD jumpAt = 0;
    static int want = 0;       // 1 = flaga +0x89 (R2), 2 = flagi +0x84/+0x8B (R1)
    static bool pulsed = false;
    if (!ctx) return;
    BYTE r1 = ctx[0x89], r2 = ctx[0x8B];
    bool e1 = r1 && !prev1, e2 = r2 && !prev2;
    prev1 = r1; prev2 = r2;
    if (g_airAtkState == kAtkLand && g_airAtkRow) {  // recovery po ladowaniu: ataki i unik dopiero w czasach ER
        float ms = AirAttackLandMs();
        if (ms < g_airAtkRow->landAtkMs) { ctx[0x84] = 0; ctx[0x8B] = 0; ctx[0x89] = 0; }
        if (ms < (g_airAtkRow->landAtkMs + g_airAtkRow->landMoveMs) / 2.f) { for (int o = 0x93; o <= 0x96; ++o) ctx[o] = 0; ctx[0x8E] = 0; }
    }
    if (!kAtkBuffer || !g_airJumpAt) { jumpAt = 0; return; }
    if (jumpAt != g_airJumpAt) { jumpAt = g_airJumpAt; want = 0; pulsed = false; }
    DWORD t = GetTickCount() - g_airJumpAt;
    if (t < kAtkBufOpenMs) {
        if (e1) want = 1; else if (e2) want = 2;
        return;
    }
    if (!want || t >= kAtkBufCloseMs || g_airAtkState != kAtkNone) { want = 0; return; }
    BYTE held = want == 1 ? r1 : r2;
    if (!pulsed) {
        pulsed = true;
        Log("[%7lu ms] atak z wyskoku: klik %s sprzed okna odtworzony w %lu ms skoku (przycisk %s)", GetTickCount() - g_t0,
            want == 1 ? "R2 (+0x89)" : "R1 (+0x84/+0x8B)", t,
            held ? "trzymany" : "puszczony");
        if (held) {  // jedna klatka bez flagi = nowe wcisniecie w nastepnej klatce
            if (want == 1) ctx[0x89] = 0; else { ctx[0x84] = 0; ctx[0x8B] = 0; }
            want = 0;
            return;
        }
    }
    if (want == 1) ctx[0x89] = 1; else { ctx[0x84] = 1; ctx[0x8B] = 1; }
    ctx[0x1C4] |= 1;
}

static void AirControlTick(float dt) {
    if (!g_airJumpAt) { if (g_mapHitOff) SetMapHit(true); return; }
    DWORD t = GetTickCount() - g_airJumpAt;
    if (g_mapHitOff && t >= kDipEndMs) SetMapHit(true);
    if (t > kAirToMs) { g_airJumpAt = 0; return; }
    if (t < kAirFromMs) return;
    if (g_momActive) return;  // spadanie: ruch poziomy idzie predkoscia (AirMomentumTick), nie zapisem pozycji
    float mag = sqrtf(g_axis[0] * g_axis[0] + g_axis[1] * g_axis[1]);
    if (mag > 1.f) mag = 1.f;
    BYTE* pos = ChrPosData();
    if (!pos) return;
    __try {
        float ang = *reinterpret_cast<float*>(pos + 0x4);
        float* x = reinterpret_cast<float*>(pos + 0x10);
        float* z = reinterpret_cast<float*>(pos + 0x18);
        float y = *reinterpret_cast<float*>(pos + 0x14);
        static float lastY = 0.f;
        bool still = fabsf(y - lastY) < 0.005f;
        lastY = y;
        if (t >= kLandCheckFromMs && still && y <= g_airY0 + 0.05f) {
            g_jumpLanded = true;  // na ziemi: koniec dosuwania, CancelLandingRollIfIdle konczy animacje
            g_airJumpAt = 0;
            if (kDiag) Log("[%7lu ms] ladowanie wykryte po %lu ms (y %.2f, start %.2f)", GetTickCount() - g_t0, t, y, g_airY0);
            return;
        }
        if (kDiag) {
            static DWORD lastLog = 0;
            if (GetTickCount() - lastLog > 100) {
                lastLog = GetTickCount();
                Log("[%7lu ms] lot +%lums: galka %.2f kat %.2f poz %.2f %.2f %.2f", GetTickCount() - g_t0, t, mag, ang,
                    *x, *reinterpret_cast<float*>(pos + 0x14), *z);
            }
        }
        if (mag < 0.2f) return;
        float step = g_airDrift * mag * dt;
        // Przod postaci = (-sin, -cos) kata (zmierzone w logu skoku 902: kat ~2.6, ruch x-, z+).
        *x -= sinf(ang) * step;
        *z -= cosf(ang) * step;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
    }
}

// --- Rozped w spadaniu po skoku ---------------------------------------------------------------
// Sonda 2026-11-11 + dekompilacja FUN_1402bbe40: w trakcie animacji skoku (+0x1F2 = 1, grawitacja
// wylaczona przez JT27) predkosc = root motion. Gra konczy animacje po ~0.7-0.85 s; 2 klatki pozniej
// wlacza grawitacje i wtedy:
//   +0x1F3 = 1 (do ladowania): predkosc = +0xD0 (poprzednia klatka),
//   +0x1F0 = 1 (swobodne spadanie): predkosc = biezaca predkosc proxy, XZ obciete do +-6 m/s na os
//   (0x1A2AE54) i mnozone co klatke przez +0xF0 (0.98).
// Handler wejscia dziala po kroku Havoka, wiec zapis proxy+0x60 i +0xD0 jest baza nastepnej klatki.
// v0.7 (po tescie v0.6: "jak trafienie w teksture, potem pchniecie"): ostatnie klatki animacji to
// autorskie ladowanie - root motion hamuje (sprint: 7.3 -> 1.3 m/s w poziomie, -6.8 -> -2 m/s w
// pionie), a po wlaczeniu grawitacji pion startuje od ~0. Dlatego:
//   1. animacje skoku konczymy sami tuz PRZED hamowaniem (MomCutMs),
//   2. przejmujemy pelny wektor ostatniej dobrej klatki lotu: X/Z do ladowania, Y do chwili, gdy
//      silnik wejdzie w swobodne spadanie (dalej sam dodaje grawitacje do tego, co dostal).
constexpr DWORD kMomSampleFromMs = 400;
constexpr DWORD kMomArmMs = 400;        // wczesniej grawitacja bywa wlaczona przez 1-2 klatki wybicia
constexpr DWORD kMomMaxMs = 8000;       // bezpiecznik (bardzo dlugi upadek, smierc, ekran ladowania)
constexpr float kMomAirAccel = 4.0f;    // m/s^2: jak szybko galka zmienia rozped w spadaniu
constexpr float kMomGravity = 9.8f;     // m/s^2 (z sondy: 0.163 m/s na klatke)
constexpr float kFallClampVanilla = 6.0f, kFallClampRaised = 12.0f;  // limit XZ na os w spadaniu
// Koniec animacji skoku [ms od zlecenia]. Z sondy: hamowanie root motion widac od klatki ~700 ms
// (900, 902) i ~830 ms (901); po naszym -1 gra odtwarza jeszcze najwyzej 1 klatke.
static DWORD MomCutMs(int anim) { return anim == kJumpAnimStanding ? 770 : 650; }

static DWORD g_momJumpAt = 0, g_momFallAt = 0, g_momGoodAt = 0;
static int g_momAnim = 0;
static bool g_momAnimOn = false;        // na warstwie 7 nadal gra animacja skoku (nie atak z wyskoku)
static bool g_momCut = false, g_momYCarry = false, g_momHasGood = false;
static float g_momSumH = 0.f, g_momMinVy = 0.f;
static int g_momN = 0;
static float g_momGood[3] = {};         // predkosc (x, y, z) ostatniej dobrej klatki lotu
static float g_mom[2] = {}, g_momVy = 0.f, g_momVmax = 0.f;
static bool g_momClampRaised = false;
static bool g_momAtk = false;           // rozped przejety przez atak z wyskoku (wlasna grawitacja do ladowania)
static bool g_momAtkAir = false;        // po przejeciu postac byla juz w powietrzu (+0x32 = 0)
static float g_momG = kMomGravity;

constexpr float kFallUpVanilla = 1.0f, kFallUpRaised = 20.0f;  // 0x1A2AE58

static void SetFallClamp(bool raised) {
    __try {
        auto p = reinterpret_cast<float*>(reinterpret_cast<BYTE*>(GetModuleHandleA(nullptr)) + 0x1A2AE54);
        if (*p == kFallClampVanilla || *p == kFallClampRaised) {
            *p = raised ? kFallClampRaised : kFallClampVanilla;
            g_momClampRaised = raised;
            // Upward speed limit in free fall (+0x1F0). Log 2026-11-12: after an early jump attack the
            // proxy velocity said 4 m/s up but the character climbed 0.013 m per frame (= 1 m/s limit).
            float* up = p + 1;
            if (*up == kFallUpVanilla || *up == kFallUpRaised) *up = raised ? kFallUpRaised : kFallUpVanilla;
        } else if (kDiag) {
            Log("rozped: limit spadania ma nieoczekiwana wartosc %.3f - nie ruszam", *p);
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        if (kDiag) Log("rozped: nie mozna zapisac limitu spadania (strona tylko do odczytu?)");
    }
}

static void AirMomentumEnd(const char* why) {
    if (g_momActive)
        Log("[%7lu ms] rozped: koniec (%s) po %lu ms spadania", GetTickCount() - g_t0, why, GetTickCount() - g_momFallAt);
    if (g_momClampRaised) SetFallClamp(false);
    g_momActive = false;
    g_momJumpAt = 0;
}

static void AirMomentumStart(int anim) {
    if (g_momJumpAt) AirMomentumEnd("nowy skok");
    g_momJumpAt = GetTickCount();
    g_momAnim = anim;
    g_momAnimOn = true;
    g_momCut = g_momYCarry = g_momHasGood = false;
    g_momAtk = false;
    g_jumpVOk = g_airAtkVOk = false;
    g_momSumH = 0.f;
    g_momMinVy = 1e9f;
    g_momN = 0;
}

static void AirMomentumOnOtherAnim() { g_momAnimOn = false; }

static void AirMomentumTick(float dt) {
    if (!g_momJumpAt) return;
    DWORD now = GetTickCount();
    DWORD t = now - g_momJumpAt;
    if (!g_momEnabled) { AirMomentumEnd("wylaczony F7"); return; }
    if (t > kMomMaxMs) { AirMomentumEnd("limit czasu"); return; }
    BYTE* ph = ChrPosData();
    if (!ph) return;
    const char* end = nullptr;
    bool doCut = false;
    __try {
        auto proxy = *reinterpret_cast<BYTE**>(ph + 0x38);
        if (reinterpret_cast<ULONG_PTR>(proxy) < 0x10000) return;
        auto v = reinterpret_cast<float*>(proxy + 0x60);
        bool gravOff = ph[0x1F2] || ph[0x1F4];
        if (!g_momActive && gravOff) {  // lot napedzany animacja - zbieramy rozped
            if (g_momAnimOn) { g_jumpV[0] = v[0]; g_jumpV[1] = v[1]; g_jumpV[2] = v[2]; g_jumpVOk = true; }
            if (t >= kMomSampleFromMs) {
                float h = sqrtf(v[0] * v[0] + v[2] * v[2]);
                bool good = (g_momN < 3 || h >= 0.8f * (g_momSumH / g_momN)) && v[1] <= g_momMinVy + 1.5f;
                if (good) {
                    g_momGood[0] = v[0]; g_momGood[1] = v[1]; g_momGood[2] = v[2];
                    g_momGoodAt = now;
                    g_momHasGood = true;
                    g_momSumH += h;
                    ++g_momN;
                    if (v[1] < g_momMinVy) g_momMinVy = v[1];
                }
            }
            if (!g_momCut && g_momAnimOn && t >= MomCutMs(g_momAnim)) { g_momCut = true; doCut = true; }
        } else if (!g_momActive && (t >= kMomArmMs || g_airAtkVOk)) {
            if (!(ph[0x1F3] || ph[0x1F0] || !ph[0x32])) {
                end = "ladowanie bez spadania";
            } else {
                float vy0 = v[1];
                g_momAtk = g_airAtkVOk;
                g_momAtkAir = false;
                g_momG = g_momAtk ? kAirAtkGravity : kMomGravity;
                if (g_momAtk) {  // atak z wyskoku: wektor z chwili ataku (pion ograniczony do szczytu skoku)
                    g_mom[0] = g_airAtkV[0] * kAirAtkHoriz; g_mom[1] = g_airAtkV[2] * kAirAtkHoriz;
                    vy0 = g_airAtkV[1] - g_momG * (now - g_airAtkVAt) / 1000.f;
                    g_airAtkVOk = false;
                } else if (g_momHasGood) {
                    g_mom[0] = g_momGood[0]; g_mom[1] = g_momGood[2];
                    float ballistic = g_momGood[1] - kMomGravity * (now - g_momGoodAt) / 1000.f;
                    if (ballistic < vy0) vy0 = ballistic;
                } else {
                    g_mom[0] = v[0]; g_mom[1] = v[2];
                }
                float mag = sqrtf(g_axis[0] * g_axis[0] + g_axis[1] * g_axis[1]);
                if (mag > 1.f) mag = 1.f;
                if (!g_momAtk && mag >= 0.2f) {  // ciaglosc z dosuwaniem pozycji w locie (AirControlTick)
                    float ang = PhysF(ph, 0x4);
                    g_mom[0] -= sinf(ang) * g_airDrift * mag;
                    g_mom[1] -= cosf(ang) * g_airDrift * mag;
                }
                float len = sqrtf(g_mom[0] * g_mom[0] + g_mom[1] * g_mom[1]);
                g_momVmax = len > kAirDriftStand ? len : kAirDriftStand;
                g_momVy = vy0 + g_momG * dt;  // nizej odejmujemy przed zapisem
                g_momYCarry = true;
                g_momActive = true;
                g_momFallAt = now;
                SetFallClamp(true);
                Log("[%7lu ms] rozped: spadanie od +%lu ms, poziom %.2f %.2f (%.2f m/s), pion %.2f (silnik %.2f), probek %d, ciecie %d, atak %d",
                    now - g_t0, t, g_mom[0], g_mom[1], len, vy0, v[1], g_momN, g_momCut ? 1 : 0, g_momAtk ? 1 : 0);
            }
        }
        if (g_momActive) {
            if (g_momAtk && !ph[0x32]) g_momAtkAir = true;
            if (g_momAtk && !g_momAtkAir && now - g_momFallAt < kAirAtkLiftMs) ph[0x1F3] = 1;  // wzlot po wczesnym ataku
            if (ph[0x32] && !ph[0x1F3]) {
                end = "ladowanie";
            } else if (!gravOff) {
                float mag = sqrtf(g_axis[0] * g_axis[0] + g_axis[1] * g_axis[1]);
                if (mag >= 0.2f) {  // galka: rozped dociaga do kierunku patrzenia (przod = -sin/-cos kata)
                    float ang = PhysF(ph, 0x4);
                    float dx = -sinf(ang) * g_momVmax - g_mom[0], dz = -cosf(ang) * g_momVmax - g_mom[1];
                    float dl = sqrtf(dx * dx + dz * dz), step = kMomAirAccel * dt;
                    if (dl <= step || dl < 1e-4f) { g_mom[0] += dx; g_mom[1] += dz; }
                    else { g_mom[0] += dx / dl * step; g_mom[1] += dz / dl * step; }
                }
                float damp = PhysF(ph, 0xF0);  // silnik pomnozy przez to predkosc proxy w swobodnym spadaniu
                if (!(damp > 0.5f && damp <= 1.0f)) damp = 1.0f;
                v[0] = g_mom[0] / damp;
                v[2] = g_mom[1] / damp;
                *reinterpret_cast<float*>(ph + 0xD0) = g_mom[0];
                *reinterpret_cast<float*>(ph + 0xD8) = g_mom[1];
                if (g_momYCarry) {  // pion: ciag dalszy luku z animacji, dopoki silnik sam nie spada
                    g_momVy -= g_momG * dt;
                    if (g_momVy < -40.f) g_momVy = -40.f;
                    v[1] = g_momVy;
                    *reinterpret_cast<float*>(ph + 0xD4) = g_momVy;
                    if (ph[0x1F0] && !g_momAtk) g_momYCarry = false;  // atak z wyskoku: pion nasz do ladowania
                }
            }
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        end = "wyjatek";
    }
    if (doCut && g_momCtx && g_origPlayAnim) {
        unsigned long long out[2] = {};
        for (int layer : {7, 23}) g_origPlayAnim(g_momCtx, out, -1, layer, 0, g_momA6, 0);
        g_jumpEnded = true;  // CancelLandingRollIfIdle nie konczy drugi raz
        g_momAnimOn = false;
        if (kDiag) Log("[%7lu ms] rozped: koniec animacji skoku %d po %lu ms (przed hamowaniem)", now - g_t0, g_momAnim, t);
    }
    if (end) AirMomentumEnd(end);
}

// --- Sonda fizyki skoku (tylko odczyt) --------------------------------------------------------
// Cel: ustalic, w ktorej klatce i w ktorym trybie ginie rozped przy skoku na nizsza polke.
// ChrPosData to kontroler fizyki postaci (analiza FUN_1402bbe40 / FUN_140379880, niezweryfikowana
// w grze): +0x32 na ziemi, +0x33 zbocze, +0x6D zachowaj predkosc w powietrzu, +0x1F0 swobodne
// spadanie, +0x1F2/+0x1F4 grawitacja wylaczona, +0x1F3, +0x1E4 skala grawitacji, +0x1B0/+0x1B4 czas
// w powietrzu, +0xF0 mnoznik XZ, +0xD0 predkosc z poprzedniej klatki, +0x38 hkpCharacterProxy
// (predkosc liniowa w proxy+0x60). Logujemy co klatke od zlecenia skoku przez kPhysProbeMs.
constexpr DWORD kPhysProbeMs = 2500;  // skok ~0.95 s + 1.5 s spadania/ladowania

static float PhysF(const BYTE* ph, int off) { return *reinterpret_cast<const float*>(ph + off); }

static void PhysProbeTick() {
    if (!g_physProbeAt) return;
    DWORD t = GetTickCount() - g_physProbeAt;
    if (t > kPhysProbeMs) { g_physProbeAt = 0; return; }
    BYTE* ph = ChrPosData();
    if (!ph) return;
    __try {
        auto proxy = *reinterpret_cast<BYTE**>(ph + 0x38);
        float vx = 0.f, vy = 0.f, vz = 0.f;
        bool hasProxy = reinterpret_cast<ULONG_PTR>(proxy) >= 0x10000;
        if (hasProxy) {
            auto v = reinterpret_cast<float*>(proxy + 0x60);
            vx = v[0]; vy = v[1]; vz = v[2];
        }
        Log("[%7lu ms] fiz +%4lums: ziemia %u zbocze %u | 6D %u 1F0 %u 1F2 %u 1F3 %u 1F4 %u | graw %.2f xz* %.2f | "
            "t_pow %.2f/%.2f | poz %.2f %.2f %.2f | v_proxy %s%.2f %.2f %.2f (xz %.2f) | v_poprz %.2f %.2f %.2f",
            GetTickCount() - g_t0, t, ph[0x32], ph[0x33], ph[0x6D], ph[0x1F0], ph[0x1F2], ph[0x1F3], ph[0x1F4],
            PhysF(ph, 0x1E4), PhysF(ph, 0xF0), PhysF(ph, 0x1B0), PhysF(ph, 0x1B4), PhysF(ph, 0x10), PhysF(ph, 0x14), PhysF(ph, 0x18),
            hasProxy ? "" : "(brak proxy) ", vx, vy, vz, sqrtf(vx * vx + vz * vz), PhysF(ph, 0xD0), PhysF(ph, 0xD4), PhysF(ph, 0xD8));
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        g_physProbeAt = 0;  // zly wskaznik - nie probujemy co klatke
    }
}

// --- Sonda dwoch pozostalych funkcji zlecania animacji (0x37A120, 0x37A170) ------------------
// Hipoteza: animacje tylko gornej czesci ciala (np. tarcza w marszu) ida jedna z nich. Logujemy
// argumenty (max 400 wpisow), zeby porownac z 0x37A040. Sygnatura nieznana - 8 argumentow.
using SubmitFn = void*(__fastcall*)(void*, void*, long long, long long, long long, long long, long long, long long);
static SubmitFn g_origSubmitB = nullptr, g_origSubmitC = nullptr;
static int g_submitLogLeft = 400;

static void LogSubmit(const char* tag, long long a3, long long a4, long long a5, long long a6) {
    if (g_submitLogLeft-- > 0)
        Log("[%7lu ms] %s a3=%lld a4=%lld a5=%lld a6=%lld", GetTickCount() - g_t0, tag, a3, a4, a5, a6);
}
static void* __fastcall SubmitBDetour(void* c, void* o, long long a3, long long a4, long long a5, long long a6, long long a7, long long a8) {
    LogSubmit("Submit120", a3, a4, a5, a6);
    return g_origSubmitB(c, o, a3, a4, a5, a6, a7, a8);
}
static void* __fastcall SubmitCDetour(void* c, void* o, long long a3, long long a4, long long a5, long long a6, long long a7, long long a8) {
    LogSubmit("Submit170", a3, a4, a5, a6);
    return g_origSubmitC(c, o, a3, a4, a5, a6, a7, a8);
}

static void InstallSubmitProbes() {
    auto base = reinterpret_cast<BYTE*>(GetModuleHandleA(nullptr));
    static const BYTE kB[] = {0x40, 0x53, 0x48, 0x83, 0xEC, 0x30, 0x48, 0x8B, 0x49, 0x20};
    static const BYTE kC[] = {0x40, 0x53, 0x48, 0x83, 0xEC, 0x50, 0x48, 0x8B, 0x49, 0x20};
    struct { BYTE* at; const BYTE* pro; void* det; void** orig; const char* name; } hooks[] = {
        {base + 0x37A120, kB, reinterpret_cast<void*>(&SubmitBDetour), reinterpret_cast<void**>(&g_origSubmitB), "0x37A120"},
        {base + 0x37A170, kC, reinterpret_cast<void*>(&SubmitCDetour), reinterpret_cast<void**>(&g_origSubmitC), "0x37A170"},
    };
    for (auto& h : hooks) {
        if (memcmp(h.at, h.pro, sizeof(kB)) != 0) { Log("sonda %s: nieoczekiwane bajty - pomijam", h.name); continue; }
        MH_STATUS st = MH_CreateHook(h.at, h.det, h.orig);
        if (st == MH_OK) st = MH_EnableHook(h.at);
        Log("sonda zlecania animacji %s: %s", h.name, MH_StatusToString(st));
    }
}

// --- Sonda roznicowa pamieci gracza przy piciu ----------------------------------------------
// Lancuch z DSROmniRoll: [WorldChrMan @0x1C77E50]+0x68 -> PlayerIns; +0x68 PlayerCtrl;
// PlayerCtrl+0x48 ActionCtrl. Migawki: A = tuz przed piciem (marsz), B = 1.5 s po zadaniu,
// C = 3.5 s po zadaniu. Logujemy dwordy z A == C != B (zmienione na czas picia).
struct MemRegion { const char* name; BYTE* ptr; size_t size; };
constexpr size_t kSnapSize = 0x800;
static BYTE g_snap[3][3][kSnapSize];  // [migawka][region][bajty]
static BYTE* g_snapPtr[3] = {};
static bool g_snapTaken[3] = {};

static bool PlayerRegions(MemRegion out[3]) {
    __try {
        auto base = reinterpret_cast<BYTE*>(GetModuleHandleA(nullptr));
        auto worldChr = *reinterpret_cast<BYTE**>(base + 0x1C77E50);
        if (!worldChr) return false;
        auto player = *reinterpret_cast<BYTE**>(worldChr + 0x68);
        if (!player) return false;
        auto ctrl = *reinterpret_cast<BYTE**>(player + 0x68);
        auto action = ctrl ? *reinterpret_cast<BYTE**>(ctrl + 0x48) : nullptr;
        out[0] = {"PlayerIns", player, kSnapSize};
        out[1] = {"PlayerCtrl", ctrl, kSnapSize};
        out[2] = {"ActionCtrl", action, kSnapSize};
        return ctrl && action;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

static void TakeSnapshot(int which) {
    MemRegion r[3];
    if (!PlayerRegions(r)) return;
    __try {
        for (int i = 0; i < 3; ++i) {
            memcpy(g_snap[which][i], r[i].ptr, r[i].size);
            g_snapPtr[i] = r[i].ptr;
        }
        g_snapTaken[which] = true;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
    }
}

static void ReportDrinkDiff() {
    static const char* names[3] = {"PlayerIns", "PlayerCtrl", "ActionCtrl"};
    for (int r = 0; r < 3; ++r) {
        int shown = 0;
        for (size_t o = 0; o + 4 <= kSnapSize && shown < 40; o += 4) {
            DWORD a = *reinterpret_cast<DWORD*>(&g_snap[0][r][o]);
            DWORD b = *reinterpret_cast<DWORD*>(&g_snap[1][r][o]);
            DWORD c = *reinterpret_cast<DWORD*>(&g_snap[2][r][o]);
            if (a == c && a != b) {
                Log("  diff %s+0x%03zX: marsz=%08lX picie=%08lX", names[r], o, a, b);
                ++shown;
            }
        }
    }
}

// --- Hang probe (ER_DIAG only, read-only) -------------------------------------------------------
// The "hang": the player stands frozen with no full-body animation while a direction is held, until a hit
// ends it (log 2026-11-13: 4.7 s after a roll ended; position and velocity constant, on the ground). The
// cause is unknown. This probe keeps a snapshot of the three player regions from the last frame the
// player was really walking, and when the frozen state lasts kHangAfterMs it logs every dword that
// differs, plus the input and DLL state. Compare several reports: fields that differ every time are the
// candidates (the drink probe found the action permissions the same way: ActionCtrl+0x1A0..0x1B7).
constexpr DWORD kHangAfterMs = 600;
static BYTE g_walkSnap[3][kSnapSize];
static bool g_walkSnapOk = false;

static void HangProbeTick(const BYTE* ctx, void* p3) {
    static float lastX = 0.f, lastZ = 0.f;
    static DWORD frozenSince = 0;
    static bool reported = false;
    BYTE* pos = ChrPosData();
    MemRegion r[3];
    if (!pos || !PlayerRegions(r)) return;
    float x = 0.f, z = 0.f;
    __try {
        x = *reinterpret_cast<float*>(pos + 0x10);
        z = *reinterpret_cast<float*>(pos + 0x18);
    } __except (EXCEPTION_EXECUTE_HANDLER) { return; }
    float step = sqrtf((x - lastX) * (x - lastX) + (z - lastZ) * (z - lastZ));
    lastX = x; lastZ = z;
    float mag = sqrtf(g_axis[0] * g_axis[0] + g_axis[1] * g_axis[1]);
    DWORD now = GetTickCount();
    bool wantsMove = mag > 0.5f && g_mainAnim == -1 && !g_airAtkMoveLock;
    if (!wantsMove || step > 0.004f) {
        if (reported && frozenSince)
            Log("[%7lu ms] HANG probe: over after %lu ms (main anim %d, step %.3f m, axes %.2f %.2f)", now - g_t0,
                now - frozenSince, g_mainAnim, step, g_axis[0], g_axis[1]);
        frozenSince = 0;
        reported = false;
        if (wantsMove && step > 0.01f && step < 1.0f && g_playerDmgAnim == -1 && g_itemUpperAnim == -1) {
            __try {
                for (int i = 0; i < 3; ++i) memcpy(g_walkSnap[i], r[i].ptr, kSnapSize);
                g_walkSnapOk = true;
            } __except (EXCEPTION_EXECUTE_HANDLER) {}
        }
        return;
    }
    if (!frozenSince) frozenSince = now ? now : 1;
    if (reported || now - frozenSince < kHangAfterMs) return;
    reported = true;
    int lockFree = -1, stamina = -1;
    DWORD chrFlags = 0;
    __try {
        auto b = static_cast<const BYTE*>(p3);
        lockFree = b[0x21D];
        auto chr = *reinterpret_cast<BYTE* const*>(b + 0x10);
        if (reinterpret_cast<ULONG_PTR>(chr) >= 0x10000) {
            stamina = *reinterpret_cast<const int*>(chr + 0x3F8);
            chrFlags = *reinterpret_cast<const DWORD*>(chr + 0x524);
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) {}
    Log("[%7lu ms] HANG probe: frozen %lu ms with a direction held (axes %.2f %.2f) | hit anim L11 %d, item anim L6 %d, "
        "drink %d, omni active %d armed %d | free-move %d stamina %d chr+0x524 %08lX", now - g_t0, now - frozenSince,
        g_axis[0], g_axis[1], g_playerDmgAnim, g_itemUpperAnim, DrinkActive() ? 1 : 0, g_omniActive ? 1 : 0,
        g_omniArmed ? 1 : 0, lockFree, stamina, chrFlags);
    __try {
        for (int from = 0x84; from < 0xD0; from += 0x26) {  // two lines: the log keeps 240 characters per line
            char line[3 * 0x26 + 8];
            int n = 0;
            for (int o = from; o < from + 0x26 && o < 0xD0; ++o) n += sprintf_s(line + n, sizeof(line) - n, "%02X ", ctx[o]);
            Log("  input ctx from +0x%02X: %s", from, line);
        }
        Log("  input ctx +0x1C4 %02X  +0x1E4 %02X  +0x224 %d  +0x260 %.3f  +0x324 %.3f  +0x328 %02X  +0x329 %02X  +0x350 %02X",
            ctx[0x1C4], ctx[0x1E4], *reinterpret_cast<const int*>(ctx + 0x224), *reinterpret_cast<const float*>(ctx + 0x260),
            *reinterpret_cast<const float*>(ctx + 0x324), ctx[0x328], ctx[0x329], ctx[0x350]);
        Log("  physics: ground %d slope %d +6D %d +1F0 %d +1F2 %d +1F3 %d +1F4 %d gravity scale %.2f", pos[0x32], pos[0x33],
            pos[0x6D], pos[0x1F0], pos[0x1F2], pos[0x1F3], pos[0x1F4], *reinterpret_cast<float*>(pos + 0x1E4));
        if (!g_walkSnapOk) { Log("  no walking snapshot yet - nothing to compare"); return; }
        for (int i = 0; i < 3; ++i) {
            int shown = 0;
            for (size_t o = 0; o + 4 <= kSnapSize && shown < 60; o += 4) {
                DWORD a = *reinterpret_cast<DWORD*>(&g_walkSnap[i][o]);
                DWORD b = *reinterpret_cast<DWORD*>(r[i].ptr + o);
                if (a != b) { Log("  hang diff %s+0x%03zX: walk=%08lX hang=%08lX", r[i].name, o, a, b); ++shown; }
            }
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) {}
}

// --- EKSPERYMENT: odblokowanie ruchu w trakcie picia ----------------------------------------
// Kandydaci z sondy roznicowej (3/3 prob): PlayerIns+0x4B3 i +0x4B7 (0 marsz, 1 picie) oraz
// zgody ActionCtrl+0x1A0..0x1B7 (1 marsz, 0 picie). Kazde kolejne picie wymusza co klatke inny
// wariant (rotacja), zeby jeden test sprawdzil wszystkich kandydatow.
static int g_drinkExperiment = -1;   // -1 brak; 0..3 aktywny wariant w trakcie picia
static int g_drinkCounter = 0;
static BYTE g_walkPerms[0x18];       // zgody ActionCtrl+0x1A0 z migawki "marsz"
static const char* kExperimentNames[] = {"PlayerIns+0x4B3=0", "PlayerIns+0x4B7=0", "oba 0x4B3+0x4B7=0",
                                         "zgody ActionCtrl+0x1A0..0x1B7 z marszu"};

static void ApplyDrinkExperiment() {
    if (g_drinkExperiment < 0) return;
    MemRegion r[3];
    if (!PlayerRegions(r)) return;
    __try {
        if (g_drinkExperiment == 0 || g_drinkExperiment == 2) r[0].ptr[0x4B3] = 0;
        if (g_drinkExperiment == 1 || g_drinkExperiment == 2) r[0].ptr[0x4B7] = 0;
        if (g_drinkExperiment == 3) memcpy(r[2].ptr + 0x1A0, g_walkPerms, sizeof(g_walkPerms));
    } __except (EXCEPTION_EXECUTE_HANDLER) {
    }
}

// Wolane co klatke z handlera wejscia. Migawka A jest robiona stale (co klatke nadpisywana),
// dopoki nie przyjdzie zadanie przedmiotu - wtedy zamraza stan "tuz przed piciem".
static void DrinkDiffProbe(bool itemRequestedNow) {
    static DWORD reqAt = 0;
    if (itemRequestedNow && !reqAt) {
        reqAt = GetTickCount();
        g_snapTaken[1] = g_snapTaken[2] = false;
        memcpy(g_walkPerms, g_snap[0][2] + 0x1A0, sizeof(g_walkPerms));
        // Eksperyment z zapisem pamieci wylaczony - blokade ruchu (SwitchMotion w ESD) zdejmuje
        // ESD z Simple Estus Walking. Sonda roznicowa dalej tylko loguje.
        ++g_drinkCounter;
        Log("[%7lu ms] sonda roznicowa: start; picie #%d", reqAt - g_t0, g_drinkCounter);
        return;
    }
    if (!reqAt) { TakeSnapshot(0); return; }
    DWORD since = GetTickCount() - reqAt;
    if (since < 3000) ApplyDrinkExperiment();
    else g_drinkExperiment = -1;
    if (since >= 1500 && !g_snapTaken[1]) TakeSnapshot(1);
    if (since >= 3500 && !g_snapTaken[2]) {
        TakeSnapshot(2);
        if (g_snapTaken[0] && g_snapTaken[1] && g_snapTaken[2]) {
            Log("[%7lu ms] sonda roznicowa: pola zmienione na czas picia (A==C!=B):", GetTickCount() - g_t0);
            ReportDrinkDiff();
        }
        reqAt = 0;
    }
}

// --- Wolny chod w trakcie picia (jak w ER) ---------------------------------------------------
// Osie ruchu (klawiatura/pad) gra pobiera funkcjami 0x1A3700 i 0x1A3750 (zrodlo: DSROmniRoll;
// zwracaja float w xmm0). W trakcie picia ograniczamy dlugosc wektora ruchu do kDrinkMoveCap -
// gra sama wybiera wtedy wolny chod. Picie aktywne: od 7585/7588 na warstwie gornej (5) do -1 po
// ostatniej czesci (7587/7588); bezpiecznik 5 s.
constexpr float kDrinkMoveCap = 0.45f;
using AxisFn = float(__fastcall*)(void*);
static AxisFn g_origAxisA = nullptr, g_origAxisB = nullptr;
// g_axis zadeklarowane wyzej (uzywa tez sterowanie w locie)
static DWORD g_drinkStart = 0;
static int g_drinkLastPart = 0;

// Picie aktywne wg pamieci gry: ID biezacej animacji akcji w ActionCtrl (+0x78; w innej sesji
// sonda pokazala +0x80 - sprawdzamy oba) w zakresie animacji picia 7585-7588. Z ESD Simple Estus
// Walking picie idzie ChangeUpperBodyAnim, ktore omija obserwowany PlayAnim (0x37A040).
// 7587 (odlozenie flaszki) trwa w TAE 2.63 s, ale od ~0.53 s mozna ja przerwac ruchem (JT11) -
// po tym czasie zdejmujemy ograniczenie, zeby powrot do biegu/sprintu nie byl opozniony.
// 2026-11-12: cancel windows of 7587 moved to ER times (movement from 0.30 s, tools\apply_estus_walk.py);
// ER lifts its walk limit 0.30 s into the put-away animation as well.
constexpr DWORD kDrinkEndReleaseMs = 300;
constexpr DWORD kDrinkPartMaxMs = 3000;
// 7586 (the sip) repeats with the same ID when the player chains drinks, so the value in ActionCtrl does not
// change and the 3 s failsafe used to lift the cap after 5-6 sips. A chain gets a long limit instead; a drink
// broken by another full-body animation is detected directly (g_itemBrokenAt, set in PlayAnimDetour).
constexpr DWORD kDrinkChainMaxMs = 22000;

// Item animations the patched ESD plays on the upper body: Estus 7585-7589, crushed items 7500 (souls)
// and 7501 (humanity).
static bool IsItemWalkAnim(int a) { return (a >= 7585 && a <= 7589) || a == 7500 || a == 7501; }
static DWORD ItemPartMaxMs(int a) {
    switch (a) {
        case 7586: return kDrinkChainMaxMs;
        case 7500: return 2600;  // TAE length 2.10 s
        case 7501: return 4700;  // TAE length 4.13 s
        default: return kDrinkPartMaxMs;
    }
}

// Called from PlayAnimDetour: a full-body animation of the player started while an item animation was in
// ActionCtrl - the item use is over, whatever stale value the game leaves behind.
static void TrackItemBreak(int animId, int layer) {
    if (layer != 7 || animId < 0 || IsItemWalkAnim(animId)) return;
    DWORD now = GetTickCount();
    g_itemBrokenAt = now ? now : 1;
}

static bool DrinkActive() {
    static int lastAnim = -1;
    static DWORD lastAnimSince = 0;
    MemRegion r[3];
    if (!PlayerRegions(r)) return false;
    int anim = -1;
    __try {
        for (int off : {0x78, 0x80}) {
            int a = *reinterpret_cast<int*>(r[2].ptr + off);
            if (IsItemWalkAnim(a)) { anim = a; break; }
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) {
    }
    if (anim != lastAnim) {
        // Diagnostic: how long each drink stage really lasted (shows whether the TAE cancel windows of
        // 7587 end the state early or the state waits for the end of the animation, 1.33 s).
        Log("[%7lu ms] drink stage: %d -> %d after %lu ms", GetTickCount() - g_t0, lastAnim, anim,
            GetTickCount() - lastAnimSince);
        lastAnim = anim;
        lastAnimSince = GetTickCount();
    }
    DWORD held = GetTickCount() - lastAnimSince;
    if (anim == 7587 && held > kDrinkEndReleaseMs) return false;
    // Broken by another full-body animation after this stage started (hit, roll, attack).
    if (anim != -1 && g_itemBrokenAt && static_cast<LONG>(g_itemBrokenAt - lastAnimSince) > 0) return false;
    // Bezpiecznik: po przerwanym piciu (trafienie) gra zostawia w ActionCtrl stara wartosc -
    // zadna czesc picia nie trwa > ~2.5 s, wiec dluzej = picie juz sie nie toczy.
    if (anim != -1 && held > ItemPartMaxMs(anim)) {
        static int warnedFor = -1;
        if (warnedFor != anim) {
            Log("[%7lu ms] picie: wartosc %d w ActionCtrl od %lu ms - uznaje za zakonczone (bezpiecznik)",
                GetTickCount() - g_t0, anim, held);
            warnedFor = anim;
        }
        return false;
    }
    return anim != -1;
}

static float CapAxis(int idx, float v) {
    g_axis[idx] = v;
    if (g_airAtkMoveLock) return 0.f;  // recovery po ladowaniu ataku z wyskoku (g_axis trzyma surowa wartosc)
    static bool wasActive = false;
    bool active = DrinkActive();
    if (active != wasActive) {
        Log("[%7lu ms] picie (ActionCtrl): %s", GetTickCount() - g_t0, active ? "start - wolny chod" : "koniec");
        wasActive = active;
    }
    if (!active) return v;
    float mag = sqrtf(g_axis[0] * g_axis[0] + g_axis[1] * g_axis[1]);
    return mag > kDrinkMoveCap ? v * (kDrinkMoveCap / mag) : v;
}
static float __fastcall AxisADetour(void* p) { return CapAxis(0, g_origAxisA(p)); }
static float __fastcall AxisBDetour(void* p) { return CapAxis(1, g_origAxisB(p)); }

// Wolane z PlayAnimDetour dla kazdego zlecenia animacji.
static void TrackDrink(int animId, int layer) {
    if (layer != 5) return;
    if (animId >= 7585 && animId <= 7588) {
        if (!g_drinkStart) Log("[%7lu ms] picie: start (wolny chod)", GetTickCount() - g_t0);
        if (!g_drinkStart || animId == 7585 || animId == 7588) g_drinkStart = GetTickCount();
        g_drinkLastPart = animId;
    } else if (animId == -1 && g_drinkStart && (g_drinkLastPart == 7587 || g_drinkLastPart == 7588)) {
        Log("[%7lu ms] picie: koniec po %lu ms", GetTickCount() - g_t0, GetTickCount() - g_drinkStart);
        g_drinkStart = 0;
    }
}

static void InstallDrinkSlowWalk() {
    auto base = reinterpret_cast<BYTE*>(GetModuleHandleA(nullptr));
    static const BYTE kPro[] = {0x48, 0x83, 0xEC, 0x38, 0x48, 0x8B, 0x05};
    struct { BYTE* at; void* det; void** orig; const char* name; } hooks[] = {
        {base + 0x1A3700, reinterpret_cast<void*>(&AxisADetour), reinterpret_cast<void**>(&g_origAxisA), "0x1A3700"},
        {base + 0x1A3750, reinterpret_cast<void*>(&AxisBDetour), reinterpret_cast<void**>(&g_origAxisB), "0x1A3750"},
    };
    for (auto& h : hooks) {
        if (memcmp(h.at, kPro, sizeof(kPro)) != 0) { Log("os ruchu %s: nieoczekiwane bajty - pomijam", h.name); continue; }
        MH_STATUS st = MH_CreateHook(h.at, h.det, h.orig);
        if (st == MH_OK) st = MH_EnableHook(h.at);
        Log("os ruchu %s (wolny chod przy piciu): %s", h.name, MH_StatusToString(st));
    }
}

// Wolane co klatke z handlera wejscia (watek gry).
static void CancelLandingRollIfIdle() {
    if (g_jumpEnded || !g_jumpAnimCtx || !g_origPlayAnim) return;
    DWORD since = GetTickCount() - g_lastJumpInject;
    if (since < kLandingCancelMs && !g_jumpLanded) return;
    g_jumpEnded = true;
    if (since > kLandingCancelMs + 500) return;  // za pozno (np. pauza) - nie ruszamy
    unsigned long long out[2] = {};
    for (int layer : {7, 23})
        g_origPlayAnim(g_jumpAnimCtx, out, -1, layer, 0, g_jumpAnimArg6, 0);
    Log("[%7lu ms] ladowanie bez inputu: wymuszone zakonczenie skoku po %lu ms", GetTickCount() - g_t0, since);
}

static void ForceEndPlayerAnim() {
    if (!g_rollCtx || !g_origPlayAnim) return;
    unsigned long long out[2] = {};
    for (int layer : {7, 23}) g_origPlayAnim(g_rollCtx, out, -1, layer, 0, g_rollA6, 0);
    Log("[%7lu ms] ===== F9: wymuszony koniec animacji gracza (7 i 23) =====", GetTickCount() - g_t0);
}

static void InstallRollPressHook() {
    auto target = reinterpret_cast<BYTE*>(GetModuleHandleA(nullptr)) + 0x1A46B0;
    if (target[0] == 0xE9 || (target[0] == 0xFF && target[1] == 0x25)) {
        Log("bufor uniku: FUN_1401a46b0 juz zahookowana przez inny modul - bufor wylaczony");
        return;
    }
    MH_STATUS st = MH_CreateHook(target, reinterpret_cast<void*>(&RollPressDetour), reinterpret_cast<void**>(&g_origRollPress));
    if (st == MH_OK) st = MH_EnableHook(target);
    if (st != MH_OK) g_origRollPress = nullptr;
    Log("bufor uniku: hook wcisniecia uniku @0x1A46B0: %s", MH_StatusToString(st));
}

static void InstallPlayAnimProbe() {
    static const BYTE kPrologue[] = {0x48, 0x89, 0x5C, 0x24, 0x08, 0x48, 0x89, 0x6C, 0x24, 0x10, 0x48, 0x89, 0x74, 0x24, 0x18, 0x57};
    auto target = reinterpret_cast<BYTE*>(GetModuleHandleA(nullptr)) + 0x37A040;
    if (memcmp(target, kPrologue, sizeof(kPrologue)) != 0) {
        Log("sonda PlayAnim: nieoczekiwane bajty @0x37A040 - pomijam");
        return;
    }
    MH_STATUS st = MH_CreateHook(target, reinterpret_cast<void*>(&PlayAnimDetour), reinterpret_cast<void**>(&g_origPlayAnim));
    if (st == MH_OK) st = MH_EnableHook(target);
    Log("sonda PlayAnim @0x37A040: %s", MH_StatusToString(st));
}

static void InstallInputProbe() {
    static const BYTE kPrologue[] = {0x48, 0x8B, 0xC4, 0x55, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56};
    auto target = reinterpret_cast<BYTE*>(GetModuleHandleA(nullptr)) + 0x396860;
    // DSROmniRoll hookuje te sama funkcje z opoznieniem i wymaga oryginalnych bajtow - gdy jest
    // zaladowany, czekamy na jego hook i zakladamy nasz na wierzchu (MinHook relokuje jego skok).
    if (GetModuleHandleA("DSROmniRoll.dll")) {
        Log("sonda wejscia: wykryto DSROmniRoll - czekam na jego hook @0x396860");
        for (int i = 0; i < 240 && memcmp(target, kPrologue, sizeof(kPrologue)) == 0; ++i) Sleep(500);
        if (memcmp(target, kPrologue, sizeof(kPrologue)) == 0) {
            Log("sonda wejscia: OmniRoll nie zalozyl hooka w 120 s - zakladam nasz");
        } else if (target[0] != 0xE9 && !(target[0] == 0xFF && target[1] == 0x25)) {
            Log("sonda wejscia: nieznany poczatek funkcji (%02X %02X) - pomijam", target[0], target[1]);
            return;
        } else {
            Log("sonda wejscia: hook OmniRoll obecny (%02X) - dokladam nasz", target[0]);
        }
    } else if (memcmp(target, kPrologue, sizeof(kPrologue)) != 0) {
        Log("sonda wejscia: nieoczekiwane bajty @0x396860 - pomijam (inny build?)");
        return;
    }
    g_t0 = GetTickCount();
    MH_STATUS st = MH_CreateHook(target, reinterpret_cast<void*>(&InputDetour), reinterpret_cast<void**>(&g_origInput));
    if (st == MH_OK) st = MH_EnableHook(target);
    Log("sonda wejscia @0x396860: %s", MH_StatusToString(st));
}

// Diagnostyka pada: co 5 s loguje, czy xinput1_3 gry widzi kontroler w slotach 0-3 i czy dane
// sie zmieniaja (dwPacketNumber). Zmiany stanu loguje od razu, stan staly - co 30 s.
static DWORD WINAPI PadDiagThread(LPVOID) {
    Sleep(60000);  // nie ruszamy XInput w trakcie startu gry (podejrzenie wplywu na wykrywanie pada)
    using GetStateFn = DWORD(WINAPI*)(DWORD, XINPUT_STATE*);
    GetStateFn getState = nullptr;
    for (int i = 0; i < 60 && !getState; ++i) {
        if (HMODULE m = GetModuleHandleA("xinput1_3.dll"))
            getState = reinterpret_cast<GetStateFn>(GetProcAddress(m, "XInputGetState"));
        if (!getState) Sleep(1000);
    }
    if (!getState) { Log("pad-diag: xinput1_3.dll nie zaladowany przez gre po 60 s"); return 0; }
    char last[64] = "";
    for (int tick = 0;; ++tick) {
        char now[64];
        int len = 0;
        for (DWORD slot = 0; slot < 4; ++slot) {
            XINPUT_STATE xs{};
            DWORD r = getState(slot, &xs);
            len += sprintf_s(now + len, sizeof(now) - len, " %lu:%s", slot, r == ERROR_SUCCESS ? "OK" : "--");
        }
        XINPUT_STATE s0{};
        DWORD packet = getState(0, &s0) == ERROR_SUCCESS ? s0.dwPacketNumber : 0;
        if (strcmp(now, last) != 0 || tick % 6 == 0)
            Log("[%7lu ms] pad-diag sloty%s, pakiet slot0=%lu", GetTickCount() - g_t0, now, packet);
        strcpy_s(last, now);
        Sleep(5000);
    }
}

// Szybkie wyjscie do pulpitu: Ctrl+Q przytrzymane 1 s, gdy okno gry jest aktywne (gra nie ma
// opcji "wyjdz do pulpitu"). Gra zapisuje postep na biezaco - jak Alt+F4.
static DWORD WINAPI QuitHotkeyThread(LPVOID) {
    int held = 0;
    for (;;) {
        Sleep(50);
        DWORD pid = 0;
        GetWindowThreadProcessId(GetForegroundWindow(), &pid);
        bool down = pid == GetCurrentProcessId() && (GetAsyncKeyState(VK_CONTROL) & 0x8000) && (GetAsyncKeyState('Q') & 0x8000);
        held = down ? held + 1 : 0;
        if (held >= 20) {
            Log("[%7lu ms] Ctrl+Q: wyjscie do pulpitu", GetTickCount() - g_t0);
            TerminateProcess(GetCurrentProcess(), 0);
        }
    }
}

// Roll-scoped Havok yaw hold around FUN_1402bb150 (RVA 0x2BB150: character physics & yaw step).
// Ensures root motion rotation (FUN_1402bbe40) and yaw integration (FUN_1402bc380) use exact OmniRoll yaw
// from Frame 0 through kOmniHoldSec without modifying input, camera, or lock-on state.
using ChrPhysStepFn = void(__fastcall*)(BYTE* posData, float dt);
static ChrPhysStepFn g_origChrPhysStep = nullptr;

static void __fastcall ChrPhysStepDetour(BYTE* posData, float dt) {
    bool hold = g_omniActive && g_omniRollOn && posData && posData == ChrPosData();
    if (hold) {
        __try {
            *reinterpret_cast<float*>(posData + 0x04) = g_omniActiveYaw;
            *reinterpret_cast<float*>(posData + 0x144) = 0.0f;
        } __except (EXCEPTION_EXECUTE_HANDLER) {
            hold = false;
        }
    }
    g_origChrPhysStep(posData, dt);
    if (hold) {
        __try {
            *reinterpret_cast<float*>(posData + 0x04) = g_omniActiveYaw;
            *reinterpret_cast<float*>(posData + 0x144) = 0.0f;
        } __except (EXCEPTION_EXECUTE_HANDLER) {}
        if (dt > 0.0f && dt < 0.2f) g_omniHoldElapsed += dt;
        if (g_omniHoldElapsed >= kOmniHoldSec) g_omniActive = false;
    }
}

static void InstallChrPhysStepHook() {
    static const BYTE kPrologue[] = {0x40, 0x57, 0x48, 0x81, 0xEC, 0x80, 0x00, 0x00, 0x00, 0x0F, 0x29, 0x7C, 0x24, 0x50};
    auto target = reinterpret_cast<BYTE*>(GetModuleHandleA(nullptr)) + 0x2BB150;
    if (memcmp(target, kPrologue, sizeof(kPrologue)) != 0) {
        Log("omniroll: unexpected prologue @0x2BB150 (%02X %02X) - skipping phys yaw hook", target[0], target[1]);
        return;
    }
    MH_STATUS st = MH_CreateHook(target, reinterpret_cast<void*>(&ChrPhysStepDetour), reinterpret_cast<void**>(&g_origChrPhysStep));
    if (st == MH_OK) st = MH_EnableHook(target);
    if (st != MH_OK) g_origChrPhysStep = nullptr;
    Log("omniroll: Havok yaw hold hook @0x2BB150: %s", MH_StatusToString(st));
}

// Deterministic wait for Arxan .text decryption and visible game window (works in ER_DIAG=0 and ER_DIAG=1).
static void WaitForGameReady() {
    static const BYTE kRollWrite[] = {0xC6, 0x87, 0x93, 0x00, 0x00, 0x00, 0x01, 0x80, 0x8F, 0xC4, 0x01, 0x00, 0x00, 0x01};
    static const BYTE kInputPro[]  = {0x48, 0x8B, 0xC4, 0x55, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56};
    static const BYTE kAnimPro[]   = {0x48, 0x89, 0x5C, 0x24, 0x08, 0x48, 0x89, 0x6C, 0x24, 0x10};
    static const BYTE kPhysPro[]   = {0x40, 0x57, 0x48, 0x81, 0xEC, 0x80, 0x00, 0x00, 0x00};
    auto base = reinterpret_cast<BYTE*>(GetModuleHandleA(nullptr));
    struct Find { DWORD pid; HWND wnd; } f{GetCurrentProcessId(), nullptr};
    bool codeReady = false;
    for (int i = 0; i < 480; ++i) {  // up to 120 s (480 * 250 ms)
        if (!f.wnd) {
            EnumWindows([](HWND w, LPARAM lp) -> BOOL {
                auto* q = reinterpret_cast<Find*>(lp);
                DWORD pid = 0;
                GetWindowThreadProcessId(w, &pid);
                if (pid == q->pid && IsWindowVisible(w)) { q->wnd = w; return FALSE; }
                return TRUE;
            }, reinterpret_cast<LPARAM>(&f));
        }
        __try {
            codeReady = memcmp(base + 0x398E4F, kRollWrite, sizeof(kRollWrite)) == 0 &&
                        memcmp(base + 0x396860, kInputPro, sizeof(kInputPro)) == 0 &&
                        memcmp(base + 0x37A040, kAnimPro, sizeof(kAnimPro)) == 0 &&
                        memcmp(base + 0x2BB150, kPhysPro, sizeof(kPhysPro)) == 0;
        } __except (EXCEPTION_EXECUTE_HANDLER) {
            codeReady = false;
        }
        if (f.wnd && codeReady) break;
        Sleep(250);
    }
    Sleep(3000);  // allow Arxan post-decryption checks to settle before installing hooks
    Log("startup: window=%s decrypted=%d - installing hooks", f.wnd ? "yes" : "timeout", codeReady ? 1 : 0);
}

static DWORD WINAPI InitThread(LPVOID) {
    if (kDiag) if (HANDLE t = CreateThread(nullptr, 0, PadDiagThread, nullptr, 0, nullptr)) CloseHandle(t);
    if (HANDLE t = CreateThread(nullptr, 0, QuitHotkeyThread, nullptr, 0, nullptr)) CloseHandle(t);
    MH_STATUS st = MH_Initialize();
    Log("MinHook: %s", MH_StatusToString(st));
    if (!GetModuleHandleA("DSROmniRoll.dll")) {
        WaitForGameReady();
    }
    if (kDiag) DumpDecryptedText();
    InstallInputProbe();
    InstallPlayAnimProbe();
    InstallRollPressHook();
    InstallChrPhysStepHook();
    if (kDiag) InstallSubmitProbes();
    InstallDrinkSlowWalk();
    return 0;
}

extern "C" HRESULT WINAPI DirectInput8Create(HINSTANCE inst, DWORD ver, REFIID iid, LPVOID* out, LPUNKNOWN outer) {
    using Fn = HRESULT(WINAPI*)(HINSTANCE, DWORD, REFIID, LPVOID*, LPUNKNOWN);
    if (!LoadReal()) return E_FAIL;
    auto fn = reinterpret_cast<Fn>(GetProcAddress(g_real, "DirectInput8Create"));
    if (!fn) return E_FAIL;
    HRESULT hr = fn(inst, ver, iid, out, outer);
    Log("DirectInput8Create(ver=%#x) -> %#x", ver, hr);
    return hr;
}

BOOL WINAPI DllMain(HMODULE self, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(self);
        OpenLog(self);
        LoadConfigIni();
        RollKeyLoad(self);
        Log("er_engine etap 0 zaladowany");
        DescribeProcess();
        // MinHook nie w DllMain (loader lock) - osobny watek.
        if (HANDLE t = CreateThread(nullptr, 0, InitThread, nullptr, 0, nullptr)) CloseHandle(t);
    } else if (reason == DLL_PROCESS_DETACH && g_log) {
        MH_Uninitialize();
        Log("er_engine wyladowany");
        fclose(g_log);
    }
    return TRUE;
}

