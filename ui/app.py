# ui/app.py

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import streamlit as st
from core.context import ContextBrief

import json
import streamlit as st
from core.context import ContextBrief
from core.session import AnalyticalState
from core.logger import init_db, get_history
from core.proactive import get_proactive_suggestions
from modes.mode1_hypotheses import generate_hypotheses
from modes.mode2_code import draft_code
from modes.mode3_synthesis import synthesise_docs
from modes.mode4_stress import stress_test_conclusion
from modes.mode5_narrative import draft_narrative

# ── Page config ────────────────────────────────────────────────
st.set_page_config(
    page_title="Analyst Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Initialize SQLite on first load ────────────────────────────
init_db()


# ── Session state bootstrap ─────────────────────────────────────
# This runs on every rerun but only initializes if key doesn't exist.
# This is the pattern for all persistent state in Streamlit.
if "analytical_state" not in st.session_state:
    st.session_state.analytical_state = AnalyticalState()

if "context_brief" not in st.session_state:
    st.session_state.context_brief = None

if "briefed" not in st.session_state:
    st.session_state.briefed = False

if "mode2_reviewed" not in st.session_state:
    st.session_state.mode2_reviewed = False

if "mode2_result" not in st.session_state:
    st.session_state.mode2_result = None

if "last_suggestions" not in st.session_state:
    st.session_state.last_suggestions = []


# ── Helper: render proactive nudges ────────────────────────────
def render_nudges(suggestions: list[dict]):
    if not suggestions:
        return
    st.markdown("---")
    st.markdown("**💡 Thought Partner Nudges**")
    for s in suggestions:
        icon = "🔴" if s["priority"] == "high" else "🟡" if s["priority"] == "medium" else "🟢"
        with st.expander(f"{icon} {s['action']}"):
            st.caption(s["reason"])


# ── Helper: render JSON result cleanly ─────────────────────────
def render_json(data: dict, exclude_keys: list[str] = None):
    exclude = exclude_keys or ["_raw", "_error"]
    clean = {k: v for k, v in data.items() if k not in exclude}
    st.json(clean)


# ════════════════════════════════════════════════════════════════
# SIDEBAR — ContextBrief
# ════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("🧠 Analyst Assistant")
    st.caption("Analytical thought partner")
    st.markdown("---")

    st.subheader("📋 Session Brief")
    st.caption("Fill this once. Every mode inherits it automatically.")

    with st.form("context_form"):
        company_name = st.text_input(
            "Company / Team",
            value="Deliveroo Care",
            placeholder="e.g. Deliveroo Care"
        )
        domain = st.text_input(
            "Domain",
            value="customer support operations",
            placeholder="e.g. customer support operations"
        )
        primary_metric = st.text_input(
            "Primary Metric",
            value="self-serve rate",
            placeholder="e.g. self-serve rate"
        )
        metric_definition = st.text_area(
            "Metric Definition",
            value="percentage of customer contacts resolved without a human agent",
            height=68,
        )
        time_period = st.text_input(
            "Time Period",
            value="last 30 days (May 2026)",
        )
        audience = st.selectbox(
            "Output Audience",
            ["data team", "executive", "ops manager"],
        )
        stakes = st.text_input(
            "Stakes",
            value="weekly ops review with Head of Care",
            placeholder="e.g. board presentation"
        )
        known_context = st.text_area(
            "Known Context",
            value="a new bot deflection flow was launched on June 1st 2026",
            height=68,
        )
        constraints = st.text_input(
            "Constraints",
            value="do not reference competitor benchmarks",
        )

        submitted = st.form_submit_button(
            "Brief the Agent",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            st.session_state.context_brief = ContextBrief(
                company_name=company_name,
                domain=domain,
                primary_metric=primary_metric,
                metric_definition=metric_definition,
                time_period=time_period,
                audience=audience,
                stakes=stakes,
                known_context=known_context,
                constraints=constraints,
            )
            # Reset analytical state on re-brief
            st.session_state.analytical_state = AnalyticalState()
            st.session_state.briefed = True
            st.session_state.mode2_reviewed = False
            st.session_state.mode2_result = None
            st.success("Agent briefed. Session started.")

    # Session status
    if st.session_state.briefed:
        state = st.session_state.analytical_state
        st.markdown("---")
        st.subheader("📊 Session Status")
        col1, col2 = st.columns(2)
        col1.metric("Turns", state.session_turn)
        col2.metric("Hypotheses", len(state.hypotheses))
        col1.metric("Evidence", len(state.evidence_collected))
        col2.metric("Open Qs", len(state.open_questions))

        if state.current_focus != "not yet determined":
            st.caption(f"**Focus:** {state.current_focus}")

    # Reset button
    st.markdown("---")
    if st.button("🔄 Reset Session", use_container_width=True):
        st.session_state.analytical_state = AnalyticalState()
        st.session_state.briefed = False
        st.session_state.context_brief = None
        st.session_state.mode2_reviewed = False
        st.session_state.mode2_result = None
        st.session_state.last_suggestions = []
        st.rerun()


# ════════════════════════════════════════════════════════════════
# MAIN AREA
# ════════════════════════════════════════════════════════════════
if not st.session_state.briefed:
    st.title("🧠 Analyst Assistant")
    st.info("👈 Fill in the Session Brief in the sidebar to begin.")
    st.markdown("""
    ### What this tool does
    
    This is a **stateful analytical thought partner** — not a chatbot, not a search engine.
    It accumulates understanding across your investigation and pushes back when your 
    conclusions outrun your evidence.
    
    **Five modes, one session:**
    - **Mode 1 — Hypotheses:** Generate ranked explanations for a pattern
    - **Mode 2 — Code:** Draft investigation code targeting your best hypothesis  
    - **Mode 3 — Synthesis:** Read multiple documents, detect contradictions
    - **Mode 4 — Stress Test:** Adversarially challenge your conclusion
    - **Mode 5 — Narrative:** Write a stakeholder-ready summary of the investigation
    
    Every mode knows what every other mode produced.
    """)
    st.stop()


# Guard: context must exist
context = st.session_state.context_brief
state = st.session_state.analytical_state

st.title(f"🧠 {context.company_name} — Analytical Session")
st.caption(f"Metric: **{context.primary_metric}** · Period: {context.time_period} · Audience: {context.audience}")
st.markdown("---")

# ── Tabs ────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "💡 Mode 1 — Hypotheses",
    "💻 Mode 2 — Code",
    "📄 Mode 3 — Synthesis",
    "🔍 Mode 4 — Stress Test",
    "✍️ Mode 5 — Narrative",
    "🕒 Session Timeline",
    "📋 Call History",
])


# ════════════════════════════════════════════════════════════════
# TAB 1 — MODE 1: HYPOTHESES
# ════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("💡 Hypothesis Generator")
    st.caption("Describe a metric pattern. Include co-moving metrics you can observe.")

    user_input = st.text_area(
        "What pattern are you investigating?",
        height=150,
        placeholder="""e.g. Self-serve rate dropped from 68% to 54% over the last 30 days.
Co-moving metrics:
- bot_deflection_rate dropped from 71% to 49%
- avg_handle_time increased from 4.2 min to 6.8 min
- contact_volume increased 22% week-over-week""",
        key="mode1_input",
    )

    if st.button("Generate Hypotheses", type="primary", key="mode1_run"):
        if not user_input.strip():
            st.warning("Describe the pattern you're investigating first.")
        else:
            with st.spinner("Generating hypotheses..."):
                result = generate_hypotheses(
                    user_input=user_input,
                    context=context,
                    state=state,
                )
                suggestions = get_proactive_suggestions(state)
                st.session_state.last_suggestions = suggestions

            # Contradiction flag
            if result.get("contradiction_flag"):
                st.error(f"⚠️ Contradiction detected: {result['contradiction_flag']}")

            # Hypotheses
            st.subheader("Ranked Hypotheses")
            for i, h in enumerate(result.get("hypotheses", []), 1):
                confidence = h.get("confidence", 0)
                with st.expander(
                    f"#{i} — {h['text']} "
                    f"({'⬆️' if confidence >= 0.7 else '➡️' if confidence >= 0.4 else '⬇️'} "
                    f"{confidence:.0%} confidence)",
                    expanded=(i == 1),
                ):
                    st.caption(f"**Co-moving metric cited:** {h.get('co_moving_metric_cited', 'N/A')}")
                    st.markdown(f"✅ **Confirms if:** {h.get('confirms_if', '')}")
                    st.markdown(f"❌ **Rules out if:** {h.get('rules_out_if', '')}")

            # Open questions
            if oqs := result.get("open_questions", []):
                st.subheader("Open Questions Flagged")
                for q in oqs:
                    st.markdown(f"- {q}")

            render_nudges(suggestions)


# ════════════════════════════════════════════════════════════════
# TAB 2 — MODE 2: CODE DRAFTER + REVIEW GATE
# ════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("💻 Code Drafter")
    st.caption("Describe what you want to investigate. The agent targets your highest-confidence hypothesis.")

    # Show active hypotheses as context
    if state.hypotheses:
        with st.expander("Active hypotheses (agent will target these)", expanded=False):
            for h in state.hypotheses:
                icon = "🟢" if h.status == "confirmed" else "🔴" if h.status == "ruled_out" else "🔵"
                st.markdown(f"{icon} **{h.confidence:.0%}** — {h.text}")

    code_input = st.text_area(
        "What do you want to investigate with code?",
        height=120,
        placeholder="e.g. Write Python to compare self-serve rate before and after June 1st, segmented by contact_reason. I have a dataframe `contacts` with columns: date, contact_reason, resolved_self_serve (bool), bot_deflected (bool), handle_time_minutes.",
        key="mode2_input",
    )

    if st.button("Draft Code", type="primary", key="mode2_run"):
        if not code_input.strip():
            st.warning("Describe what you want to investigate first.")
        else:
            with st.spinner("Drafting code..."):
                result = draft_code(
                    user_input=code_input,
                    context=context,
                    state=state,
                )
                st.session_state.mode2_result = result
                # Reset review gate on new generation
                st.session_state.mode2_reviewed = False
                suggestions = get_proactive_suggestions(state)
                st.session_state.last_suggestions = suggestions

    # Render result + review gate
    if st.session_state.mode2_result:
        result = st.session_state.mode2_result

        if result.get("refusal_reason") and result["refusal_reason"] != "null":
            st.error(f"⚠️ {result['refusal_reason']}")
        else:
            # Hypothesis targeted
            if h_tested := result.get("hypothesis_tested"):
                st.info(f"🎯 Targeting hypothesis: *{h_tested}*")

            # Assumptions
            if assumptions := result.get("assumptions", []):
                with st.expander("⚠️ Assumptions made"):
                    for a in assumptions:
                        st.markdown(f"- {a}")

            # Code block — always visible
            st.subheader(f"Generated {result.get('language', 'code').upper()}")
            code_str = result.get("code", "")
            st.code(code_str, language=result.get("language", "python"))

            # Interpretation guide
            if guide := result.get("interpretation_guide"):
                st.markdown(f"**Interpretation:** {guide}")

            st.markdown("---")

            # ── REVIEW GATE ──────────────────────────────────────
            # This is the structural judgment boundary.
            # Copy is disabled until the analyst confirms review.
            st.markdown("### ✋ Review Gate")
            st.caption(
                "Read the code carefully before copying. "
                "Check the box to confirm you understand it before copying is enabled."
            )

            reviewed = st.checkbox(
                "I have read and understood this code. I accept responsibility for running it.",
                key="review_checkbox",
                value=st.session_state.mode2_reviewed,
            )

            if reviewed:
                st.session_state.mode2_reviewed = True

            if st.session_state.mode2_reviewed:
                st.success("✅ Review confirmed. Copy the code above to run it.")
                # Show copy-ready block with confirmation
                st.code(code_str, language=result.get("language", "python"))
            else:
                st.warning("⬆️ Check the box above to enable copying.")

        render_nudges(st.session_state.last_suggestions)


# ════════════════════════════════════════════════════════════════
# TAB 3 — MODE 3: DOCUMENT SYNTHESIS
# ════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("📄 Document Synthesiser")
    st.caption("Paste 2–5 document excerpts. The agent detects contradictions and cross-references the analytical state.")

    st.markdown("**Source documents** (minimum 2 required)")

    docs = []
    for i in range(1, 4):
        doc = st.text_area(
            f"Source {i}",
            height=100,
            placeholder=f"Paste source {i} here...",
            key=f"doc_{i}",
        )
        if doc.strip():
            docs.append(doc.strip())

    if st.button("Synthesise Documents", type="primary", key="mode3_run"):
        if len(docs) < 2:
            st.warning("Provide at least 2 source documents.")
        else:
            with st.spinner("Synthesising..."):
                result = synthesise_docs(
                    documents=docs,
                    context=context,
                    state=state,
                )
                suggestions = get_proactive_suggestions(state)
                st.session_state.last_suggestions = suggestions

            st.subheader(f"Synthesis ({result.get('source_count', len(docs))} sources)")

            # Synthesis summary
            if summary := result.get("synthesis_summary"):
                st.markdown(f"**Summary:** {summary}")

            col1, col2 = st.columns(2)

            with col1:
                if facts := result.get("facts", []):
                    st.markdown("**✅ Facts (explicitly stated)**")
                    for f in facts:
                        st.markdown(f"- {f}")

                if inferences := result.get("inferences", []):
                    st.markdown("**🔍 Inferences (logical conclusions)**")
                    for inf in inferences:
                        st.markdown(f"- {inf}")

            with col2:
                if gaps := result.get("gaps", []):
                    st.markdown("**❓ Gaps (missing information)**")
                    for g in gaps:
                        st.markdown(f"- {g}")

            # Conflicts — highlighted prominently
            if conflicts := result.get("conflicts", []):
                st.markdown("---")
                st.subheader("⚠️ Conflicts Detected")
                for c in conflicts:
                    severity_color = (
                        "🔴" if c["severity"] == "critical"
                        else "🟡" if c["severity"] == "moderate"
                        else "🟢"
                    )
                    with st.expander(f"{severity_color} {c['severity'].upper()} conflict"):
                        st.markdown(f"**Source A says:** {c['source_a']}")
                        st.markdown(f"**Source B says:** {c['source_b']}")
            else:
                st.success("✅ No conflicts detected between sources.")

            # State contradictions
            if sc := result.get("state_contradictions"):
                st.warning(f"⚠️ Contradicts analytical state: {sc}")

            render_nudges(suggestions)


# ════════════════════════════════════════════════════════════════
# TAB 4 — MODE 4: STRESS TEST
# ════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("🔍 Conclusion Stress-Tester")
    st.caption("State your conclusion. The agent will challenge it using everything it knows from this session.")

    if state.hypotheses:
        with st.expander("Session hypotheses (agent will reference these)", expanded=False):
            for h in state.hypotheses:
                st.markdown(f"- **{h.confidence:.0%}** — {h.text}")

    conclusion_input = st.text_area(
        "State your conclusion",
        height=100,
        placeholder="e.g. The self-serve rate drop is primarily caused by the bot confidence threshold being set too conservatively, not by the volume spike from the campaign.",
        key="mode4_input",
    )

    if st.button("Stress Test", type="primary", key="mode4_run"):
        if not conclusion_input.strip():
            st.warning("State a conclusion to stress-test first.")
        else:
            with st.spinner("Stress-testing..."):
                result = stress_test_conclusion(
                    conclusion=conclusion_input,
                    context=context,
                    state=state,
                )
                suggestions = get_proactive_suggestions(state)
                st.session_state.last_suggestions = suggestions

            # Verdict — prominent display
            verdict = result.get("verdict", "UNKNOWN")
            verdict_color = (
                "🟢" if verdict == "STRONG"
                else "🟡" if verdict == "NEEDS WORK"
                else "🔴"
            )
            st.markdown(f"## {verdict_color} Verdict: {verdict}")
            st.caption(result.get("verdict_reason", ""))

            # Hypotheses referenced
            if refs := result.get("hypotheses_referenced", []):
                st.subheader("Hypotheses Referenced")
                for r in refs:
                    st.markdown(f"- {r}")

            # Flaws
            if flaws := result.get("flaws", []):
                st.subheader("Flaws Identified")
                for flaw in flaws:
                    severity_icon = (
                        "🔴" if flaw["severity"] == "critical"
                        else "🟡" if flaw["severity"] == "moderate"
                        else "🟢"
                    )
                    with st.expander(
                        f"{severity_icon} {flaw['type'].replace('_', ' ').title()} — {flaw['severity'].upper()}"
                    ):
                        st.markdown(flaw["description"])

            # Strengthening analysis
            if sa := result.get("strengthening_analysis"):
                st.info(f"💪 **To strengthen this conclusion:** {sa}")

            # Ignored ruled-out hypotheses
            if ignored := result.get("ignored_ruled_out_hypotheses"):
                st.warning(f"⚠️ **Ignored ruled-out hypothesis:** {ignored}")

            render_nudges(suggestions)


# ════════════════════════════════════════════════════════════════
# TAB 5 — MODE 5: NARRATIVE WRITER
# ════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("✍️ Narrative Writer")
    st.caption(f"Writes for your briefed audience: **{context.audience}**. Draws on the full session.")

    narrative_input = st.text_area(
        "Any specific focus for the narrative? (optional)",
        height=80,
        placeholder="e.g. Focus on the bot investigation findings. Keep it to 3 paragraphs.",
        key="mode5_input",
    )

    if st.button("Draft Narrative", type="primary", key="mode5_run"):
        focus = narrative_input.strip() or f"Write a narrative for the {context.audience} summarising this investigation."
        with st.spinner("Drafting narrative..."):
            result = draft_narrative(
                user_input=focus,
                context=context,
                state=state,
            )

        # Narrative text
        st.subheader("Narrative")
        narrative_text = result.get("narrative", "")
        st.markdown(narrative_text)

        # Flags
        if flags := result.get("flags", []):
            st.markdown("---")
            st.subheader("🚩 Flags in Narrative")
            for flag in flags:
                flag_type = flag.get("type", "")
                icon = (
                    "🔴" if flag_type == "HIGH STAKES"
                    else "🟡" if flag_type == "CONTESTED"
                    else "⚪"
                )
                with st.expander(f"{icon} [{flag_type}] — {flag['claim'][:60]}..."):
                    st.markdown(f"**Claim:** {flag['claim']}")
                    st.markdown(f"**Reason flagged:** {flag['reason']}")

        # Summary footer
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**✅ What we know:**\n{result.get('what_we_know', '')}")
        col2.markdown(f"**❓ What we don't know:**\n{result.get('what_we_dont_know', '')}")
        col3.markdown(f"**➡️ Next step:**\n{result.get('recommended_next_step', '')}")


# ════════════════════════════════════════════════════════════════
# TAB 6 — SESSION TIMELINE
# ════════════════════════════════════════════════════════════════
with tab6:
    st.subheader("🕒 Session Timeline")
    st.caption("Every mode call this session, in order.")

    if not state.thread:
        st.info("No mode calls yet this session. Run a mode to see the timeline.")
    else:
        for event in reversed(state.thread):
            mode_label = event.mode.replace("_", " ").title()
            with st.expander(
                f"Turn {event.turn} — {mode_label} — {event.timestamp[:19]}",
                expanded=False,
            ):
                st.markdown(f"**Input:** {event.user_input[:200]}...")
                st.markdown(f"**Output preview:** {event.agent_output[:300]}...")

    # Analytical state dump
    st.markdown("---")
    st.subheader("Current Analytical State")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Hypotheses**")
        if state.hypotheses:
            for h in state.hypotheses:
                icon = "🟢" if h.status == "confirmed" else "🔴" if h.status == "ruled_out" else "🔵"
                st.markdown(f"{icon} ({h.confidence:.0%}) {h.text}")
        else:
            st.caption("None yet.")

        st.markdown("**Conclusions Stated**")
        if state.conclusions_stated:
            for c in state.conclusions_stated:
                st.markdown(f"- {c[:100]}...")
        else:
            st.caption("None yet.")

    with col2:
        st.markdown("**Evidence Collected**")
        if state.evidence_collected:
            for e in state.evidence_collected:
                st.markdown(f"- {e}")
        else:
            st.caption("None yet.")

        st.markdown("**Open Questions**")
        if state.open_questions:
            for q in state.open_questions:
                st.markdown(f"- {q}")
        else:
            st.caption("None yet.")


# ════════════════════════════════════════════════════════════════
# TAB 7 — CALL HISTORY
# ════════════════════════════════════════════════════════════════
with tab7:
    st.subheader("📋 Call History")
    st.caption("Every LLM call ever made through this tool — prompt version, latency, full output.")

    history = get_history(limit=50)

    if not history:
        st.info("No calls logged yet.")
    else:
        # Summary metrics
        total_calls = len(history)
        avg_latency = sum(h["latency_ms"] for h in history) / total_calls
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Calls", total_calls)
        col2.metric("Avg Latency", f"{avg_latency:.0f}ms")
        col3.metric("Prompt Versions", len(set(h["prompt_version"] for h in history)))

        st.markdown("---")

        for call in history:
            with st.expander(
                f"{call['timestamp'][:19]} — {call['mode']} — {call['latency_ms']}ms — v{call['prompt_version']}",
                expanded=False,
            ):
                st.markdown(f"**Mode:** `{call['mode']}`")
                st.markdown(f"**Prompt version:** `{call['prompt_version']}`")
                st.markdown(f"**Latency:** {call['latency_ms']}ms")
                st.markdown(f"**Input:**")
                st.text(call["user_input"][:400])
                st.markdown(f"**Output:**")
                st.text(call["full_output"][:600])