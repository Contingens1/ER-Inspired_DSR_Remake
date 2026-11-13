// Lists every instruction with a memory operand [reg + disp] where disp is one of the given offsets (any operand
// size), with the instruction text and the containing function. Used to find who sets / tests one flag field,
// e.g. the "move requested" bit ActionCtrl+0x1DC (byte +0x1DE, bit 0x10).
// Arguments: <output_file> <offset> [offset ...]   (offsets in hex or decimal, e.g. 0x1DC 0x1DE)
// @category ER_Engine

import ghidra.app.script.GhidraScript;
import ghidra.program.model.lang.Register;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.scalar.Scalar;

import java.io.PrintWriter;
import java.util.HashSet;
import java.util.Set;

public class FindFieldAccess extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        Set<Long> wanted = new HashSet<>();
        for (int i = 1; i < args.length; i++) wanted.add(Long.decode(args[i]));
        int n = 0;
        try (PrintWriter w = new PrintWriter(args[0], "UTF-8")) {
            for (Instruction ins : currentProgram.getListing().getInstructions(true)) {
                if (monitor.isCancelled()) break;
                for (int op = 0; op < ins.getNumOperands(); op++) {
                    String rep = ins.getDefaultOperandRepresentation(op);
                    if (!rep.contains("[")) continue;  // memory operands only
                    boolean hasReg = false;
                    Long disp = null;
                    for (Object o : ins.getOpObjects(op)) {
                        if (o instanceof Register) hasReg = true;
                        if (o instanceof Scalar) disp = ((Scalar) o).getSignedValue();
                    }
                    if (!hasReg || disp == null || !wanted.contains(disp)) continue;
                    Function f = getFunctionContaining(ins.getAddress());
                    w.println(ins.getAddress() + "\t" + (f != null ? f.getName() + "@" + f.getEntryPoint() : "?") + "\t"
                              + String.format("+0x%X", disp) + "\t" + ins.toString());
                    n++;
                    break;
                }
            }
        }
        println("FindFieldAccess done: " + n + " instructions -> " + args[0]);
    }
}
