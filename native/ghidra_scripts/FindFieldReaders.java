// Szuka funkcji, ktore odczytuja bajty pod podanymi offsetami pola (np. flagi zadan akcji
// +0x92/+0x93/+0xAE/+0x8E). Argumenty: <offset> [offset ...]. Wypisuje funkcje uzywajace
// najwiekszej liczby roznych offsetow (dyspozytor akcji).
// @category ER_Engine
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.scalar.Scalar;
import ghidra.program.model.lang.Register;
import java.util.*;

public class FindFieldReaders extends GhidraScript {
    @Override
    public void run() throws Exception {
        Set<Long> wanted = new HashSet<>();
        for (String a : getScriptArgs()) wanted.add(Long.decode(a));
        Map<Function, Set<Long>> hits = new HashMap<>();
        for (Instruction ins : currentProgram.getListing().getInstructions(true)) {
            if (monitor.isCancelled()) break;
            for (int op = 0; op < ins.getNumOperands(); op++) {
                Object[] objs = ins.getOpObjects(op);
                boolean hasReg = false;
                Long disp = null;
                for (Object o : objs) {
                    if (o instanceof Register) hasReg = true;
                    if (o instanceof Scalar) disp = ((Scalar) o).getSignedValue();
                }
                // operand pamieci [reg + disp] rozmiaru bajtu
                if (!hasReg || disp == null || !wanted.contains(disp)) continue;
                String rep = ins.getDefaultOperandRepresentation(op);
                if (!rep.contains("byte ptr")) continue;
                Function f = getFunctionContaining(ins.getAddress());
                if (f != null) hits.computeIfAbsent(f, k -> new TreeSet<>()).add(disp);
            }
        }
        hits.entrySet().stream()
            .filter(e -> e.getValue().size() >= 2)
            .sorted((a, b) -> b.getValue().size() - a.getValue().size())
            .limit(20)
            .forEach(e -> println("FUNC " + e.getKey().getEntryPoint() + " offsety=" + e.getValue()));
    }
}
