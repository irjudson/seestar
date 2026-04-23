// DumpWifiFuncs.java — Ghidra headless post-script
// Finds every function that references WiFi/escan/sound-33/country strings
// and writes the decompiled C-like output to <outdir>/<binary>/<func>.c
// Also emits a sorted func list so 5.50 and 5.82 outputs diff cleanly.

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import ghidra.program.model.data.*;
import ghidra.program.model.mem.*;
import java.io.*;
import java.util.*;

public class DumpWifiFuncs extends GhidraScript {

    // Strings whose references identify the functions we want.
    private static final String[] NEEDLES = new String[] {
        "Escan set error",
        "wl_run_escan",
        "RestartWifi",
        "repeat RestartWifi",
        "first error, RestartWifi",
        "exceed max retry time",
        "en33.wav",
        "en30.wav",
        "en31.wav",
        "en34.wav",
        "en39.wav",
        "WiFi abnormal",
        "wl country",
        "dhd_conf_set_country",
        "dhd_conf_map_country_list",
        "ap_id_inited",
        "ifconfig wlan0 down",
        "ifconfig uap0 down",
        "systemctl restart hostapd",
        "CFG80211-ERROR",
        "pi_reset_ap_id_passwd"
    };

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String outDir = args.length > 0 ? args[0] : "out";
        String binaryLabel = args.length > 1 ? args[1] : getCurrentProgram().getName();
        File base = new File(outDir, binaryLabel);
        base.mkdirs();

        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        // Collect addresses of matching strings
        Listing listing = currentProgram.getListing();
        Memory mem = currentProgram.getMemory();
        ReferenceManager refs = currentProgram.getReferenceManager();
        FunctionManager funcs = currentProgram.getFunctionManager();

        Set<Function> targets = new HashSet<>();
        Map<String, Set<String>> stringHits = new TreeMap<>();

        DataIterator di = listing.getDefinedData(true);
        int scanned = 0;
        while (di.hasNext() && !monitor.isCancelled()) {
            Data d = di.next();
            if (!(d.getDataType() instanceof StringDataType) &&
                !d.getDataType().getName().toLowerCase().contains("string")) continue;
            Object val = d.getValue();
            if (!(val instanceof String)) continue;
            String s = (String) val;
            scanned++;
            for (String needle : NEEDLES) {
                if (!s.contains(needle)) continue;
                stringHits.computeIfAbsent(needle, k -> new TreeSet<>()).add(s);
                Address addr = d.getAddress();
                ReferenceIterator it = refs.getReferencesTo(addr);
                while (it.hasNext()) {
                    Reference r = it.next();
                    Function f = funcs.getFunctionContaining(r.getFromAddress());
                    if (f != null) targets.add(f);
                }
            }
        }

        // Summary file
        try (PrintWriter pw = new PrintWriter(new File(base, "_summary.txt"))) {
            pw.println("# binary: " + binaryLabel);
            pw.println("# defined strings scanned: " + scanned);
            pw.println("# needles matched:");
            for (Map.Entry<String, Set<String>> e : stringHits.entrySet()) {
                pw.println("## " + e.getKey());
                for (String s : e.getValue()) pw.println("  " + s.replace("\n", "\\n"));
            }
            pw.println();
            pw.println("# referencing functions (" + targets.size() + "):");
            List<Function> sorted = new ArrayList<>(targets);
            sorted.sort(Comparator.comparing(Function::getName));
            for (Function f : sorted) pw.println(f.getName() + " @ " + f.getEntryPoint());
        }

        // Decompile each target
        for (Function f : targets) {
            if (monitor.isCancelled()) break;
            String name = f.getName();
            // Sanitize filename
            String safe = name.replaceAll("[^A-Za-z0-9_.-]", "_");
            File outFile = new File(base, safe + ".c");
            DecompileResults res = decomp.decompileFunction(f, 60, monitor);
            try (PrintWriter pw = new PrintWriter(outFile)) {
                pw.println("// " + name + " @ " + f.getEntryPoint());
                if (res != null && res.decompileCompleted()) {
                    pw.print(res.getDecompiledFunction().getC());
                } else {
                    pw.println("// decompile failed: " + (res == null ? "null" : res.getErrorMessage()));
                }
            }
        }

        decomp.dispose();
        println("Done. " + targets.size() + " functions dumped to " + base.getAbsolutePath());
    }
}
