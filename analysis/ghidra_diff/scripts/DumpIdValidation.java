// DumpIdValidation.java — Ghidra headless post-script
// Hunt for ID-validation / hardware-fingerprint-check code paths:
//   - MAC address reads/compares
//   - /proc/cpuinfo Serial reads
//   - License file reads + SN/CPU_ID compare
//   - Any "is_verified" / "pi_is_verified" / "verify" logic
// These would be the mechanism by which a device refuses to function
// normally if its on-disk state (from a donor image) disagrees with
// its hardware-derived identity.

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import ghidra.program.model.data.*;
import ghidra.program.model.mem.*;
import java.io.*;
import java.util.*;

public class DumpIdValidation extends GhidraScript {
    private static final String[] NEEDLES = new String[] {
        "/proc/cpuinfo",
        "Serial",
        "cpuId",
        "cpu_id",
        "/sys/class/net/",
        "wlan0/address",
        "/sys/class/ieee80211",
        "zwoair_license",
        "auth_code",
        "digest",
        "sign",
        "/home/pi/.ZWO/zwoair_license",
        "sn",
        "is_verified",
        "pi_is_verified",
        "verify_client",
        "get_verify_str",
        "rfkill",
        "/sys/class/rfkill",
        "escan",
        "wl_run_escan",
        "DHD_DCMD",
        "cntry_list",
        "country_list",
        "ap_id",
        "ap_id_inited",
        "pi_reset_ap_id_passwd",
        "setting2/network"
    };

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String outDir = args.length > 0 ? args[0] : "out_ids";
        String binaryLabel = args.length > 1 ? args[1] : getCurrentProgram().getName();
        File base = new File(outDir, binaryLabel);
        base.mkdirs();

        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        Listing listing = currentProgram.getListing();
        ReferenceManager refs = currentProgram.getReferenceManager();
        FunctionManager funcs = currentProgram.getFunctionManager();

        Set<Function> targets = new HashSet<>();
        Map<String, Set<String>> stringHits = new TreeMap<>();
        Map<String, Set<String>> funcNeedles = new TreeMap<>();

        DataIterator di = listing.getDefinedData(true);
        while (di.hasNext() && !monitor.isCancelled()) {
            Data d = di.next();
            if (!(d.getDataType() instanceof StringDataType) &&
                !d.getDataType().getName().toLowerCase().contains("string")) continue;
            Object val = d.getValue();
            if (!(val instanceof String)) continue;
            String s = (String) val;
            for (String needle : NEEDLES) {
                if (!s.contains(needle)) continue;
                stringHits.computeIfAbsent(needle, k -> new TreeSet<>()).add(s);
                Address addr = d.getAddress();
                ReferenceIterator it = refs.getReferencesTo(addr);
                while (it.hasNext()) {
                    Reference r = it.next();
                    Function f = funcs.getFunctionContaining(r.getFromAddress());
                    if (f != null) {
                        targets.add(f);
                        funcNeedles.computeIfAbsent(f.getName(), k -> new TreeSet<>()).add(needle);
                    }
                }
            }
        }

        try (PrintWriter pw = new PrintWriter(new File(base, "_summary.txt"))) {
            pw.println("# binary: " + binaryLabel);
            pw.println();
            pw.println("# needles with hits:");
            for (Map.Entry<String, Set<String>> e : stringHits.entrySet()) {
                pw.println("## " + e.getKey() + "  (" + e.getValue().size() + " strings)");
                for (String s : e.getValue()) pw.println("  " + s.replace("\n", "\\n"));
            }
            pw.println();
            pw.println("# referencing functions (" + targets.size() + "), with needles each touches:");
            List<String> sorted = new ArrayList<>(funcNeedles.keySet());
            Collections.sort(sorted);
            for (String name : sorted) {
                pw.println(name + "  :: " + String.join(", ", funcNeedles.get(name)));
            }
        }

        for (Function f : targets) {
            if (monitor.isCancelled()) break;
            String safe = f.getName().replaceAll("[^A-Za-z0-9_.-]", "_");
            File outFile = new File(base, safe + ".c");
            DecompileResults res = decomp.decompileFunction(f, 60, monitor);
            try (PrintWriter pw = new PrintWriter(outFile)) {
                pw.println("// " + f.getName() + " @ " + f.getEntryPoint());
                pw.println("// needles: " + String.join(", ", funcNeedles.get(f.getName())));
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
