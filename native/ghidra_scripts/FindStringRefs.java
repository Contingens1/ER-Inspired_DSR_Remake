// Finds ASCII strings (exact, zero-terminated) and lists every reference to them, with the instructions
// around a code reference (Lua binding registration: the function pointer is usually loaded next to the name)
// or the neighbouring qwords for a data reference (binding tables).
// Arguments: <output_file> <string> [string ...]
// @category ER_Engine
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.symbol.Reference;
import java.io.PrintWriter;

public class FindStringRefs extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        Memory mem = currentProgram.getMemory();
        Listing listing = currentProgram.getListing();
        try (PrintWriter w = new PrintWriter(args[0], "UTF-8")) {
            for (int i = 1; i < args.length; i++) {
                byte[] pat = (args[i] + "\0").getBytes("US-ASCII");
                Address start = mem.getMinAddress();
                int found = 0;
                while (start != null && found < 8) {
                    Address a = mem.findBytes(start, pat, null, true, monitor);
                    if (a == null) break;
                    found++;
                    // the byte before must be 0 (exact string, not a suffix of a longer name)
                    boolean exact = true;
                    try { exact = mem.getByte(a.subtract(1)) == 0; } catch (Exception e) { }
                    w.println("== \"" + args[i] + "\" @ " + a + (exact ? "" : " (suffix of a longer string)"));
                    for (Reference r : getReferencesTo(a)) {
                        Address from = r.getFromAddress();
                        Function f = getFunctionContaining(from);
                        w.println("  ref from " + from + " in " + (f == null ? "?" : f.getEntryPoint() + " " + f.getName()) + " type " + r.getReferenceType());
                        Instruction ins = listing.getInstructionAt(from);
                        if (ins != null) {
                            Instruction p = ins;
                            for (int k = 0; k < 4 && p.getPrevious() != null; k++) p = p.getPrevious();
                            for (int k = 0; k < 10 && p != null; k++, p = p.getNext())
                                w.println("     " + p.getAddress() + (p.getAddress().equals(from) ? " > " : "   ") + p);
                        } else {
                            for (int k = -2; k <= 3; k++) {
                                Address q = from.add(k * 8L);
                                try { w.println(String.format("     %s %s %016x", q, k == 0 ? ">" : " ", mem.getLong(q))); } catch (Exception e) { }
                            }
                        }
                    }
                    start = a.add(1);
                }
                if (found == 0) w.println("== \"" + args[i] + "\" not found");
            }
        }
        println("FindStringRefs done: " + args[0]);
    }
}
