// Szuka instrukcji z podanymi stalymi natychmiastowymi. Argumenty: <plik_csv> <wartosc> [wartosc ...]
// Wypisuje funkcje z trafieniami (najwiecej trafien najpierw).
// @category ER_Engine
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.scalar.Scalar;
import java.io.PrintWriter;
import java.util.*;

public class FindImmediates extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        Set<Long> wanted = new HashSet<>();
        for (int i = 1; i < args.length; i++) wanted.add(Long.decode(args[i]));
        Map<String, Integer> perFunc = new TreeMap<>();
        try (PrintWriter w = new PrintWriter(args[0], "UTF-8")) {
            w.println("address,function,value,instruction");
            for (Instruction ins : currentProgram.getListing().getInstructions(true)) {
                if (monitor.isCancelled()) break;
                for (int op = 0; op < ins.getNumOperands(); op++) {
                    for (Object o : ins.getOpObjects(op)) {
                        if (!(o instanceof Scalar) || !wanted.contains(((Scalar) o).getSignedValue())) continue;
                        Function f = getFunctionContaining(ins.getAddress());
                        String fn = f == null ? "?" : f.getEntryPoint().toString();
                        w.println(ins.getAddress() + "," + fn + "," + ((Scalar) o).getSignedValue() + ",\"" + ins + "\"");
                        perFunc.merge(fn, 1, Integer::sum);
                    }
                }
            }
        }
        perFunc.entrySet().stream().sorted((a, b) -> b.getValue() - a.getValue()).limit(30)
            .forEach(e -> println("FUNC " + e.getKey() + " trafien=" + e.getValue()));
    }
}
