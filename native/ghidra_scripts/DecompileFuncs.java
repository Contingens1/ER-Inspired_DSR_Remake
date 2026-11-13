// Dekompiluje wskazane funkcje do plikow C. Argumenty: <katalog_wyjscia> <adres1> [adres2 ...]
// @category ER_Engine
import ghidra.app.decompiler.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import java.io.PrintWriter;

public class DecompileFuncs extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);
        for (int i = 1; i < args.length; i++) {
            Function f = getFunctionContaining(toAddr(Long.parseUnsignedLong(args[i], 16)));
            if (f == null) { println("brak funkcji @ " + args[i]); continue; }
            DecompileResults r = dec.decompileFunction(f, 300, monitor);
            String c = r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// blad: " + r.getErrorMessage();
            try (PrintWriter w = new PrintWriter(args[0] + "/FUN_" + args[i] + ".c", "UTF-8")) { w.print(c); }
            println("zapisano FUN_" + args[i] + " = " + f.getEntryPoint() + " (" + c.length() + " znakow), wolajacych: " + f.getCallingFunctions(monitor).size());
            for (Function caller : f.getCallingFunctions(monitor)) println("   caller " + caller.getEntryPoint() + " " + caller.getName());
        }
        dec.dispose();
    }
}

