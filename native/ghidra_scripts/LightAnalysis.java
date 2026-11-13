// Pre-script: wylacza najciezsze analizatory, zeby analiza 50 MB exe DSR trwala rozsadnie.
// @category ER_Engine
import ghidra.app.script.GhidraScript;

public class LightAnalysis extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] off = {
            "Decompiler Parameter ID", "Decompiler Switch Analysis", "Call Convention ID",
            "Stack", "Non-Returning Functions - Discovered", "Windows x86 PE RTTI Analyzer",
            "Demangler Microsoft", "Embedded Media", "Data Reference", "DWARF",
        };
        // Druga sekcja .text (rva 0x2019000, ~18 MB) to kod zabezpieczenia Arxan - jej analiza
        // wyczerpuje 24 GB sterty. Logika gry jest w pierwszej .text, wiec usuwamy ten blok.
        ghidra.program.model.mem.Memory mem = currentProgram.getMemory();
        ghidra.program.model.mem.MemoryBlock arxan = mem.getBlock(toAddr(0x142019000L));
        if (arxan != null) {
            println("usuwam blok " + arxan.getName() + " @ " + arxan.getStart() + " rozmiar " + arxan.getSize());
            mem.removeBlock(arxan, monitor);
        }
        for (String name : off) {
            try {
                setAnalysisOption(currentProgram, name, "false");
            } catch (Exception e) {
                println("pomijam opcje: " + name);
            }
        }
    }
}
