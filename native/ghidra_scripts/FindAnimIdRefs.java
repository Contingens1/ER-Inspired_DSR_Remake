// Post-script: szuka instrukcji z natychmiastowymi stalymi = ID animacji gracza DSR
// (przewroty 700-743, backstep/skok 680-698, uzycie przedmiotow 6400-6526).
// Wynik: plik CSV (adres instrukcji, funkcja, stala, tekst instrukcji) w katalogu z argumentu.
// @category ER_Engine
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.scalar.Scalar;
import java.io.PrintWriter;
import java.util.*;

public class FindAnimIdRefs extends GhidraScript {
    @Override
    public void run() throws Exception {
        String outDir = getScriptArgs().length > 0 ? getScriptArgs()[0] : ".";
        Set<Long> wanted = new HashSet<>();
        for (long v = 680; v <= 743; v++) wanted.add(v);
        for (long v = 6400; v <= 6526; v++) wanted.add(v);

        Listing listing = currentProgram.getListing();
        Map<String, Integer> perFunc = new TreeMap<>();
        try (PrintWriter w = new PrintWriter(outDir + "/anim_id_refs.csv", "UTF-8")) {
            w.println("address,function,value,instruction");
            for (Instruction ins : listing.getInstructions(true)) {
                if (monitor.isCancelled()) break;
                for (int op = 0; op < ins.getNumOperands(); op++) {
                    for (Object o : ins.getOpObjects(op)) {
                        if (!(o instanceof Scalar)) continue;
                        long v = ((Scalar) o).getSignedValue();
                        if (!wanted.contains(v)) continue;
                        Function f = getFunctionContaining(ins.getAddress());
                        String fn = f == null ? "?" : f.getEntryPoint().toString();
                        w.println(ins.getAddress() + "," + fn + "," + v + ",\"" + ins + "\"");
                        perFunc.merge(fn, 1, Integer::sum);
                    }
                }
            }
        }
        // Funkcje z wieloma trafieniami = najpewniej logika wyboru animacji.
        perFunc.entrySet().stream()
            .sorted((a, b) -> b.getValue() - a.getValue())
            .limit(25)
            .forEach(e -> println("FUNC " + e.getKey() + " trafien=" + e.getValue()));
    }
}
