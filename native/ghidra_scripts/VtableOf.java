// MSVC RTTI: finds the vtable(s) of a class by its mangled name and prints selected slots.
// Arguments: <output_file> <slot offsets, e.g. 0xF8,0x8> <".?AVName@NS@@"> [...]
// @category ER_Engine
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.Memory;
import java.io.PrintWriter;

public class VtableOf extends GhidraScript {
    private byte[] le(long v, int n) { byte[] b = new byte[n]; for (int i = 0; i < n; i++) b[i] = (byte) (v >> (8 * i)); return b; }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        Memory mem = currentProgram.getMemory();
        long base = currentProgram.getImageBase().getOffset();
        String[] slots = args[1].split(",");
        try (PrintWriter w = new PrintWriter(args[0], "UTF-8")) {
            for (int i = 2; i < args.length; i++) {
                Address name = mem.findBytes(mem.getMinAddress(), (args[i] + "\0").getBytes("US-ASCII"), null, true, monitor);
                if (name == null) { w.println(args[i] + ": name not found"); continue; }
                long td = name.getOffset() - 0x10;
                w.println(args[i] + ": TypeDescriptor " + Long.toHexString(td));
                Address s = mem.getMinAddress();
                while (true) {
                    Address hit = mem.findBytes(s, le(td - base, 4), null, true, monitor);
                    if (hit == null) break;
                    s = hit.add(1);
                    Address col = hit.subtract(0xC);
                    try { if (mem.getInt(col) != 1) continue; } catch (Exception e) { continue; }   // COL signature 1 on x64
                    Address vref = mem.findBytes(mem.getMinAddress(), le(col.getOffset(), 8), null, true, monitor);
                    while (vref != null) {
                        Address vt = vref.add(8);
                        w.println("  COL " + col + " offset " + mem.getInt(col.add(4)) + " -> vtable " + vt);
                        for (String sl : slots) {
                            long off = Long.decode(sl.trim());
                            long fp = mem.getLong(vt.add(off));
                            Function f = getFunctionAt(toAddr(fp));
                            w.println(String.format("     [+0x%X] %x %s", off, fp, f == null ? "" : f.getName()));
                        }
                        vref = mem.findBytes(vref.add(1), le(col.getOffset(), 8), null, true, monitor);
                    }
                }
            }
        }
        println("VtableOf done");
    }
}
