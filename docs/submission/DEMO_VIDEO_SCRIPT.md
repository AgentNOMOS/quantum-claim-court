# Demo video script: Quantum Claim Court (target 2:30)

## Recording instructions for the owner

1. **Browser and window:** use Chrome, Edge or Firefox 153+ (not Safari). Set the window to about 1440×900 and zoom to 100%. Close other tabs and turn off notifications.
2. **Recorder:** OBS, Loom or the Windows Game Bar (Win+G). Record the browser window plus your microphone.
3. **Before recording:**
   - open the Qollab project and select the **built-in simulator** (basic_simulator);
     (R3b: the app also runs on IonQ's free remote simulator. The script below assumes the built-in, ideal simulator. If you film an IonQ-simulator Run instead, its noise model can push the numbers below 5/6. In that case read the yellow noise-model notice in Scene C aloud, and replace "both confidence intervals contain it" with what the screen shows. Never film an IonQ quantum computer: the app refuses it anyway.)
   - **press Run once and record from that moment**, so the live counts on screen come from the Run you are filming;
   - do not re-run during the take.
4. **Numbers:** read every number **from the screen**. The bracketed lines below are not to be read as fixed values. Do not quote the earlier 1347/327/326 run as if it were on screen.
5. **Labels:** every "Challenge the court" result shows a **LOCAL EVALUATION** badge. Say "local evaluation" when you show it.
6. **Upload:** upload to YouTube (Unlisted or Public), Loom, Vimeo or Google Drive, with **viewing allowed without sign-in**. Test the link in a private window.

---

| Time | Screen | Narration |
|---|---|---|
| **00:00–00:15** | Title area of the app, status pill visible | "Can a quantum state be copied perfectly? Many people say yes. Physics says no. But how would you *check* a claim like that? This is Quantum Claim Court." |
| **00:15–00:35** | Scene A: scroll the docket; click the filter "Blocked", then "Needs measurement" | "Eighteen scientific claims are on trial. Some are supported, some are blocked, some must be rewritten. Only a few can be decided by measurement. The rest depend on the literature and on mathematics. The court keeps those apart." |
| **00:35–00:55** | Scene B: the three source cards; point at "Full text reviewed: no" | "These are the original papers: Wootters and Zurek's no-cloning theorem from 1982, Bužek and Hillery's approximate copier, and Bruß and colleagues, who showed that the best universal copy reaches five-sixths. For each paper you see exactly what we checked: the record and the abstract. No one reviewed the full text, and the court never pretends otherwise." |
| **00:55–01:20** | Scene C: circuit, then counts table, then fidelity chart | "Here is the real circuit: three qubits. The input becomes clone A, a blank qubit becomes clone B, and a machine qubit absorbs the disturbance. This Run executed it once, as one job, on Qollab's simulator. *[Read from screen:]* Clone A matched the original in ___ of 2000 shots, clone B in ___. The exact prediction is five-sixths, and both confidence intervals contain it. Good copies, but not perfect ones, just as the theory says." |
| **01:20–01:45** | Scene D: the witness table; click the row for "Unknown quantum states can be copied perfectly" | "Three witnesses testify on every claim: literature, mathematics and measurement. For 'unknown states can be copied perfectly', mathematics contradicts it. The no-cloning theorem rules it out. Our measurement is shown only as context, because one finite run can never prove a theorem. So the verdict is: Blocked." |
| **01:45–02:15** | Scene E: case file RT7; then Challenge the court. Select statement "optimal fidelity is 5/6": citation Deutsch & Jozsa → REWRITE; citation Bruß et al. → SUPPORTED; framing "this experiment proves it" → REWRITE; citation "forged DOI" → BLOCKED | "Now challenge the court. Same statement, different citations. A real paper about a different topic: rewrite. The right paper: supported. Add 'and this experiment proves it': rewrite, because a finite run cannot prove a theorem. A fabricated DOI: blocked. These rulings are a local evaluation of fixed building blocks. No new quantum job runs, and the measurement stays exactly as recorded." |
| **02:15–02:30** | Scene F: green cross-check list; click "Copy evidence"; show the verifier command | "Finally, the evidence. Your browser re-checks the counts and hashes. That shows consistency, not origin. The exact evidence text can be verified offline by an independent script. Ideal simulator, one input state, finite shots: the limits are stated, not hidden. Quantum Claim Court. Supported by Qollab and IonQ." |

**Word count:** about 380 words, roughly 2:25–2:35 at a calm pace. If you run long, shorten the 00:35–00:55 segment.

**Do not say:** "proves the no-cloning theorem", "verified on quantum hardware", "fact-checks any scientific claim", or "authenticated provenance".
