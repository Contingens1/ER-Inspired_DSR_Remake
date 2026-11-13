// For each address: the C string there (if any), 8 qwords from it, and every reference to it with the
// referencing function. Strings containing a substring: pass "s:<text>" (lists up to 60 matches).
// Arguments: <output_file> <hex address | s:text> ...
// @category ER_Engine
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.symbol.Reference;
import java.io.PrintWriter;

public class InspectAddrs extends GhidraScript {
    private String cstr(Memory mem, Address a) {
        StringBuilder sb = new StringBuilder();
        try {
            for (int i = 0; i < 120; i++) {
                byte b = mem.getByte(a.add(i));
                if (b == 0) break;
                if (b < 32 || b > 126) return null;
                sb.append((char) b);
            }
        } catch (Exception e) { return null; }
        return sb.length() >= 3 ? sb.toString() : null;
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        Memory mem = currentProgram.getMemory();
        try (PrintWriter w = new PrintWriter(args[0], "UTF-8")) {
            for (int i = 1; i < args.length; i++) {
                if (args[i].startsWith("s:")) {
                    byte[] pat = args[i].substring(2).getBytes("US-ASCII");
                    Address start = mem.getMinAddress();
                    int n = 0;
                    while (start != null && n < 60) {
                        Address a = mem.findBytes(start, pat, null, true, monitor);
                        if (a == null) break;
                        Address s = a;
                        while (s.getOffset() > 0 && mem.getByte(s.subtract(1)) >= 32 && mem.getByte(s.subtract(1)) <= 126) s = s.subtract(1);
                        w.println(args[i] + " @ " + s + " \"" + cstr(mem, s) + "\" refs " + getReferencesTo(s).length);
                        n++;
                        start = a.add(1);
                    }
                    continue;
                }
                Address a = toAddr(Long.parseUnsignedLong(args[i], 16));
                String s = cstr(mem, a);
                w.println("== " + a + (s != null ? " \"" + s + "\"" : ""));
                for (int k = 0; k < 8; k++) {
                    try {
                        long v = mem.getLong(a.add(k * 8L));
                        Address va = null;
                        try { va = toAddr(v); } catch (Exception e) { }
                        String vs = va != null && mem.contains(va) ? cstr(mem, va) : null;
                        Function vf = va != null && mem.contains(va) ? getFunctionAt(va) : null;
                        w.println(String.format("   +%02X %016x%s%s", k * 8, v, vs != null ? " \"" + vs + "\"" : "", vf != null ? " FUNC " + vf.getName() : ""));
                    } catch (Exception e) { }
                }
                for (Reference r : getReferencesTo(a)) {
                    Function f = getFunctionContaining(r.getFromAddress());
                    Instruction ins = currentProgram.getListing().getInstructionAt(r.getFromAddress());
                    w.println("   ref " + r.getFromAddress() + " " + r.getReferenceType() + " in " + (f == null ? "?" : f.getEntryPoint().toString()) + (ins != null ? "  " + ins : ""));
                }
            }
        }
        println("InspectAddrs done");
    }
}
