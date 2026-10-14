"""
Script to generate the SynapseTutor AI Presentation for Internship Review.
Creates SynapseTutor_AI_Internship_Presentation.pptx in 16:9 widescreen format.
Includes a dedicated AI & Machine Learning Model Inventory matrix slide.
"""

import os
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# --- Color Palette (Modern Dark Slate & Cyan Theme) ---
BG_COLOR = RGBColor(15, 23, 42)          # Slate 900 #0F172A
CARD_BG = RGBColor(30, 41, 59)           # Slate 800 #1E293B
CARD_BORDER = RGBColor(51, 65, 85)       # Slate 700 #334155
CARD_HIGHLIGHT = RGBColor(15, 118, 110)  # Teal dark #0F766E

COLOR_CYAN = RGBColor(56, 189, 248)       # Sky 400 #38BDF8 (Primary Accent)
COLOR_AMBER = RGBColor(245, 158, 11)     # Amber 500 #F59E0B (Diagnostic / Warning Accent)
COLOR_PURPLE = RGBColor(168, 85, 247)    # Purple 500 #A855F7
COLOR_GREEN = RGBColor(34, 197, 94)      # Green 500 #22C55E
COLOR_WHITE = RGBColor(248, 250, 252)    # Slate 50 #F8FAFC
COLOR_SLATE_200 = RGBColor(226, 232, 240)# Slate 200 #E2E8F0
COLOR_SLATE_400 = RGBColor(148, 163, 184)# Slate 400 #94A3B8

FONT_HEADING = "Segoe UI"
FONT_BODY = "Segoe UI"

def set_slide_background(slide):
    """Fill slide with dark navy background."""
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = BG_COLOR

def add_header(slide, title_text, category_text="SYNAPSETUTOR AI • ARCHITECTURE & ENGINEERING"):
    """Add standardized high-tech header to a slide."""
    header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(1.1))
    tf = header_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    
    # Category tag
    p_cat = tf.paragraphs[0]
    p_cat.text = category_text.upper()
    p_cat.font.name = FONT_HEADING
    p_cat.font.size = Pt(11)
    p_cat.font.bold = True
    p_cat.font.color.rgb = COLOR_CYAN
    p_cat.space_after = Pt(4)
    
    # Main title
    p_title = tf.add_paragraph()
    p_title.text = title_text
    p_title.font.name = FONT_HEADING
    p_title.font.size = Pt(24)
    p_title.font.bold = True
    p_title.font.color.rgb = COLOR_WHITE

def add_card(slide, left, top, width, height, bg_color=CARD_BG, border_color=CARD_BORDER):
    """Create a styled card box for content grouping."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    shape.line.color.rgb = border_color
    shape.line.width = Pt(1.5)
    return shape

def add_bullet(tf, title, body, bullet_color=COLOR_CYAN, title_color=COLOR_WHITE, body_color=COLOR_SLATE_200, pt_size=13):
    p = tf.add_paragraph()
    p.space_after = Pt(8)
    
    # Bullet marker / title
    run_t = p.add_run()
    run_t.text = f"•  {title}: " if title else "•  "
    run_t.font.name = FONT_BODY
    run_t.font.size = Pt(pt_size)
    run_t.font.bold = True
    run_t.font.color.rgb = title_color
    
    # Body text
    run_b = p.add_run()
    run_b.text = body
    run_b.font.name = FONT_BODY
    run_b.font.size = Pt(pt_size)
    run_b.font.bold = False
    run_b.font.color.rgb = body_color

def set_speaker_notes(slide, notes_text):
    notes_slide = slide.notes_slide
    tf = notes_slide.notes_text_frame
    tf.text = notes_text


def build_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # =========================================================================
    # SLIDE 1: Title Slide
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1)
    
    # Glow Card / Header container
    add_card(s1, Inches(0.8), Inches(1.2), Inches(11.733), Inches(5.1), bg_color=CARD_BG, border_color=CARD_BORDER)
    
    # Top Accent Badge
    badge = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(1.6), Inches(3.6), Inches(0.45))
    badge.fill.solid()
    badge.fill.fore_color.rgb = RGBColor(14, 116, 144)
    badge.line.color.rgb = COLOR_CYAN
    badge.line.width = Pt(1)
    btf = badge.text_frame
    bp = btf.paragraphs[0]
    bp.alignment = PP_ALIGN.CENTER
    bp.text = "⚡ MULTIMODAL AI HACKATHON 2026"
    bp.font.name = FONT_HEADING
    bp.font.size = Pt(11)
    bp.font.bold = True
    bp.font.color.rgb = COLOR_WHITE
    
    # Title Text Frame
    tb1 = s1.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(11.0), Inches(3.8))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    
    p = tf1.paragraphs[0]
    p.text = "SynapseTutor AI"
    p.font.name = FONT_HEADING
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE
    p.space_after = Pt(6)
    
    p2 = tf1.add_paragraph()
    p2.text = "Multimodal Adaptive Tutoring & Cognitive Modeling Platform"
    p2.font.name = FONT_HEADING
    p2.font.size = Pt(22)
    p2.font.bold = True
    p2.font.color.rgb = COLOR_CYAN
    p2.space_after = Pt(20)
    
    p3 = tf1.add_paragraph()
    p3.text = "Track D: Personalized Tutoring & Adaptive Learning • Internship Technical Presentation"
    p3.font.name = FONT_BODY
    p3.font.size = Pt(14)
    p3.font.color.rgb = COLOR_SLATE_200
    p3.space_after = Pt(22)
    
    # Key Highlights row
    p4 = tf1.add_paragraph()
    p4.text = "Key Models & Engine: "
    p4.font.name = FONT_BODY
    p4.font.size = Pt(13)
    p4.font.bold = True
    p4.font.color.rgb = COLOR_AMBER
    
    run = p4.add_run()
    run.text = "Ollama qwen2.5:7b (CUDA GPU) | MiniLM-L6-v2 | FlashRank | Scikit-Learn ML | Bayesian Knowledge Tracing"
    run.font.name = FONT_BODY
    run.font.size = Pt(13)
    run.font.color.rgb = COLOR_SLATE_200

    set_speaker_notes(s1, 
        "Good morning / afternoon, Sir. Today I am presenting SynapseTutor AI, an end-to-end cognitive tutoring platform built for Track D: Personalized Tutoring & Adaptive Learning. "
        "Unlike generic LLM wrappers that merely generate text, SynapseTutor integrates true cognitive learner modeling via Bayesian Knowledge Tracing, multi-source ingestion with exact citation anchoring, "
        "a cold-start diagnostic baseline test, and local GPU acceleration using Ollama qwen2.5:7b on CUDA."
    )

    # =========================================================================
    # SLIDE 2: Problem Statement & Motivation
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2)
    add_header(s2, "The Core Problem in AI-Powered Education")
    
    # Left Card: Traditional AI Limitations
    add_card(s2, Inches(0.8), Inches(1.7), Inches(5.6), Inches(5.1))
    tb_s2_left = s2.shapes.add_textbox(Inches(1.1), Inches(1.9), Inches(5.0), Inches(4.7))
    tf_l = tb_s2_left.text_frame
    tf_l.word_wrap = True
    
    p = tf_l.paragraphs[0]
    p.text = "Limitations of Generic LLM Tutors"
    p.font.name = FONT_HEADING
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = RGBColor(239, 68, 68) # Red accent
    p.space_after = Pt(14)
    
    add_bullet(tf_l, "Hallucinations & Ungrounded Answers", "Provide convincing answers that contradict the professor's slides or course syllabus with zero traceability.", title_color=RGBColor(252, 165, 165))
    add_bullet(tf_l, "One-Size-Fits-All Explanations", "Treat a struggling novice and an advanced learner identically; cannot gauge cognitive readiness.", title_color=RGBColor(252, 165, 165))
    add_bullet(tf_l, "The Cold-Start Dilemma", "Tutors don't know where the student stands without lengthy interrogation, causing early fatigue.", title_color=RGBColor(252, 165, 165))
    add_bullet(tf_l, "Memory Amnesia", "Each chat session resets context; past mistakes, misconceptions, and breakthroughs are instantly forgotten.", title_color=RGBColor(252, 165, 165))
    add_bullet(tf_l, "Trivial Question Generation", "Quizzes repeat identical questions or generate mathematically unverified, incorrect distractors.", title_color=RGBColor(252, 165, 165))

    # Right Card: SynapseTutor Cognitive Solution
    add_card(s2, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.1))
    tb_s2_right = s2.shapes.add_textbox(Inches(7.1), Inches(1.9), Inches(5.1), Inches(4.7))
    tf_r = tb_s2_right.text_frame
    tf_r.word_wrap = True
    
    p = tf_r.paragraphs[0]
    p.text = "SynapseTutor Cognitive Architecture"
    p.font.name = FONT_HEADING
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN
    p.space_after = Pt(14)
    
    add_bullet(tf_r, "Canonical Source Anchoring", "Strict RAG grounded to exact PDF pages, PPTX slides, and video timestamps with 0% fake citations.", title_color=COLOR_CYAN)
    add_bullet(tf_r, "Bayesian Knowledge Tracing (BKT)", "Mathematical state modeling tracking concept mastery P(L) in real-time with Ebbinghaus forgetting decay.", title_color=COLOR_CYAN)
    add_bullet(tf_r, "Quick Diagnostic Baseline Test", "Instantly calibrates learner prior mastery on course entry, eliminating cold-start uncertainty.", title_color=COLOR_AMBER)
    add_bullet(tf_r, "3-Tier Cognitive Memory", "Short-term active dialogue turns, Long-term relational mastery, and Episodic breakthrough timeline.", title_color=COLOR_CYAN)
    add_bullet(tf_r, "Self-Verifying Adaptive Assessments", "SymPy deterministic math verifier and dense cosine novelty checker (0% question repetition).", title_color=COLOR_CYAN)

    set_speaker_notes(s2, 
        "Sir, existing solutions like ChatGPT or generic wrappers fail in university settings for five fundamental reasons: hallucinations without citations, inability to track what students know, "
        "cold-start friction, memory amnesia, and unverified quiz questions. SynapseTutor addresses this by grounding knowledge directly to course material, mathematically tracking student mastery via BKT, "
        "and utilizing a 3-tier memory architecture."
    )

    # =========================================================================
    # SLIDE 3: System Architecture (4-Layer Breakdown)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3)
    add_header(s3, "End-to-End 4-Layer System Architecture")
    
    col_w = Inches(2.75)
    gap = Inches(0.24)
    top_pos = Inches(1.7)
    height_pos = Inches(5.1)
    
    # Layer 1: Frontend
    add_card(s3, Inches(0.8), top_pos, col_w, height_pos)
    tb = s3.shapes.add_textbox(Inches(0.95), top_pos + Inches(0.2), col_w - Inches(0.3), height_pos - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "LAYER 1\nInteractive UI"
    p.font.name = FONT_HEADING
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = COLOR_CYAN
    p.space_after = Pt(10)
    add_bullet(tf, "React 19 & Vite", "Blazing-fast modern single-page frontend application.", pt_size=11)
    add_bullet(tf, "Tailwind CSS", "Sleek dark-mode glassmorphic user experience.", pt_size=11)
    add_bullet(tf, "KaTeX Math Engine", "Renders inline LaTeX equations \\(...\\) and blocks \\[...\\].", pt_size=11)
    add_bullet(tf, "Source Viewer Drawer", "Slide-over drawer displaying exact source PDF / slide / video.", pt_size=11)
    add_bullet(tf, "5 Core Workspaces", "Dashboard, Tutor Chat, Adaptive Tests, Courses, Profile.", pt_size=11)

    # Layer 2: Cognitive Engine (FastAPI)
    add_card(s3, Inches(0.8) + (col_w + gap), top_pos, col_w, height_pos)
    tb = s3.shapes.add_textbox(Inches(0.95) + (col_w + gap), top_pos + Inches(0.2), col_w - Inches(0.3), height_pos - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "LAYER 2\nCognitive Engine"
    p.font.name = FONT_HEADING
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = COLOR_AMBER
    p.space_after = Pt(10)
    add_bullet(tf, "FastAPI Orchestrator", "Async Python microservice with typed Pydantic models.", pt_size=11)
    add_bullet(tf, "Multimodal Ingest", "PyMuPDF (PDF), python-pptx (Slides), Faster-Whisper (Video).", pt_size=11)
    add_bullet(tf, "BKT & Scikit-Learn", "Random Forest classifier & Gradient Boosting regressor.", pt_size=11)
    add_bullet(tf, "3-Tier Memory", "Short-term dialog, Long-term DB, Episodic timeline.", pt_size=11)
    add_bullet(tf, "Assessment Verifier", "SymPy math solver & cosine novelty checker.", pt_size=11)

    # Layer 3: AI & Compute
    add_card(s3, Inches(0.8) + (col_w + gap)*2, top_pos, col_w, height_pos)
    tb = s3.shapes.add_textbox(Inches(0.95) + (col_w + gap)*2, top_pos + Inches(0.2), col_w - Inches(0.3), height_pos - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "LAYER 3\nAI Compute Layer"
    p.font.name = FONT_HEADING
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = COLOR_PURPLE
    p.space_after = Pt(10)
    add_bullet(tf, "Ollama qwen2.5:7b", "Running 7B LLM locally on NVIDIA RTX GPU via CUDA.", pt_size=11)
    add_bullet(tf, "all-MiniLM-L6-v2", "Sentence-Transformers 384-d dense embedding model.", pt_size=11)
    add_bullet(tf, "FlashRank Reranker", "Cross-encoder scoring for high precision passage selection.", pt_size=11)
    add_bullet(tf, "Cloud/Mock Fallback", "Graceful try/catch fallback to Gemini / Mock on offline states.", pt_size=11)
    add_bullet(tf, "Zero API Cost", "Runs fully local on hardware without mandatory cloud tokens.", pt_size=11)

    # Layer 4: Storage
    add_card(s3, Inches(0.8) + (col_w + gap)*3, top_pos, col_w, height_pos)
    tb = s3.shapes.add_textbox(Inches(0.95) + (col_w + gap)*3, top_pos + Inches(0.2), col_w - Inches(0.3), height_pos - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "LAYER 4\nHybrid Storage"
    p.font.name = FONT_HEADING
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN
    p.space_after = Pt(10)
    add_bullet(tf, "SQLite WAL Mode", "Zero-config ACID relational persistence with AsyncSQLAlchemy.", pt_size=11)
    add_bullet(tf, "ChromaDB Store", "Persistent embedded vector database for dense chunk search.", pt_size=11)
    add_bullet(tf, "Immutable Metadata", "Stores source coordinates (Slide #, Page #, Timestamp).", pt_size=11)
    add_bullet(tf, "Episodic Event Logs", "Persistent JSON logs of learner milestones and misconceptions.", pt_size=11)
    add_bullet(tf, "Clean Onboarding", "Zero mock seeds; clean initialization for every new user.", pt_size=11)

    set_speaker_notes(s3, 
        "Here is our 4-layer architecture diagram: Layer 1 is React 19 + TypeScript frontend with KaTeX math rendering and Source Drawer. "
        "Layer 2 is our FastAPI backend housing the cognitive algorithms and BKT engine. Layer 3 is the local AI compute running Ollama qwen2.5:7b on NVIDIA CUDA GPU. "
        "Layer 4 is hybrid storage pairing SQLite in WAL mode with ChromaDB vector store."
    )

    # =========================================================================
    # SLIDE 4: Dedicated AI & ML Models Inventory (NEW SLIDE)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4)
    add_header(s4, "AI & Machine Learning Models Used in Platform", "COMPREHENSIVE MODEL INVENTORY & RUNTIMES")
    
    col_w2 = Inches(5.7)
    gap2 = Inches(0.33)
    top_pos2 = Inches(1.65)
    h_pos2 = Inches(5.2)

    # Left Column: Generative AI, Multimodal & Speech Models
    add_card(s4, Inches(0.8), top_pos2, col_w2, h_pos2)
    tb_m_left = s4.shapes.add_textbox(Inches(1.0), top_pos2 + Inches(0.2), col_w2 - Inches(0.4), h_pos2 - Inches(0.4))
    tf_ml_box = tb_m_left.text_frame
    tf_ml_box.word_wrap = True
    
    p = tf_ml_box.paragraphs[0]
    p.text = "Generative LLMs, Vision & Speech Models"
    p.font.name = FONT_HEADING
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = COLOR_CYAN
    p.space_after = Pt(10)
    
    add_bullet(tf_ml_box, "Ollama qwen2.5:7b (Primary LLM)", 
               "7-billion parameter instruct model running locally on NVIDIA GeForce RTX GPU via CUDA. Powers grounded Socratic tutoring, query disambiguation, and question generation with zero external API fees.", 
               title_color=COLOR_CYAN, pt_size=11)
    add_bullet(tf_ml_box, "Google Gemini 2.0 Flash (Cloud LLM)", 
               "Integrated via modern google-genai SDK as an alternative high-throughput cloud provider for low-latency synthesis and multimodal reasoning.", 
               title_color=COLOR_CYAN, pt_size=11)
    add_bullet(tf_ml_box, "qwen3-vl:4b / Gemini 2.0 Vision", 
               "Multimodal Vision-Language Models used in the visual ingestion pipeline to parse architecture diagrams, flowcharts, tables, and textbook figures into structured JSON.", 
               title_color=COLOR_PURPLE, pt_size=11)
    add_bullet(tf_ml_box, "Faster-Whisper (OpenAI Whisper)", 
               "CTranslate2-accelerated Whisper speech-to-text model (base/small). Ingests lecture MP4/WAV audio and extracts timestamped transcripts (MM:SS) for canonical source anchoring.", 
               title_color=COLOR_GREEN, pt_size=11)

    # Right Column: Embeddings, Reranker, Cognitive & Classical ML Models
    add_card(s4, Inches(0.8) + col_w2 + gap2, top_pos2, col_w2, h_pos2)
    tb_m_right = s4.shapes.add_textbox(Inches(1.0) + col_w2 + gap2, top_pos2 + Inches(0.2), col_w2 - Inches(0.4), h_pos2 - Inches(0.4))
    tf_mr_box = tb_m_right.text_frame
    tf_mr_box.word_wrap = True
    
    p = tf_mr_box.paragraphs[0]
    p.text = "Embeddings, Rerankers, Classical ML & Math"
    p.font.name = FONT_HEADING
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = COLOR_AMBER
    p.space_after = Pt(10)
    
    add_bullet(tf_mr_box, "all-MiniLM-L6-v2 (Embeddings)", 
               "Sentence-Transformers 384-dimensional dense embedding model. Indexes course chunks into ChromaDB for high-speed dense vector similarity search and question novelty cosine checks.", 
               title_color=COLOR_AMBER, pt_size=11)
    add_bullet(tf_mr_box, "FlashRank (ms-marco-TinyBERT)", 
               "Lightweight cross-encoder neural reranker that scores query-document pairs to rerank the top hybrid BM25 + dense candidates before LLM prompt injection.", 
               title_color=COLOR_AMBER, pt_size=11)
    add_bullet(tf_mr_box, "Bayesian Knowledge Tracing (BKT)", 
               "Probabilistic Hidden Markov cognitive model updating mastery P(L_t) using Slip P(S)=0.10, Guess P(G)=0.20, Learning Transition P(T)=0.15, and Ebbinghaus forgetting decay.", 
               title_color=COLOR_CYAN, pt_size=11)
    add_bullet(tf_mr_box, "Scikit-Learn Random Forest Classifier", 
               "100-tree ensemble classifying student pedagogical readiness into ready_for_next, needs_practice, or prerequisite_gap states.", 
               title_color=COLOR_GREEN, pt_size=11)
    add_bullet(tf_mr_box, "Scikit-Learn Gradient Boosting Regressor", 
               "Trained regressor predicting expected quiz score and estimated study minutes needed to attain an 80% mastery threshold.", 
               title_color=COLOR_GREEN, pt_size=11)
    add_bullet(tf_mr_box, "SymPy Symbolic Mathematics Engine", 
               "Deterministic Computer Algebra System (CAS) that verifies algebraic, arithmetic, and logic answers to guarantee zero hallucinations in generated test questions.", 
               title_color=COLOR_PURPLE, pt_size=11)

    set_speaker_notes(s4, 
        "Sir, this slide provides an explicit inventory of all models used in SynapseTutor AI. For generation and reasoning, we use local Ollama qwen2.5:7b running on our laptop's NVIDIA RTX GPU via CUDA, "
        "with Google Gemini 2.0 Flash as an optional cloud alternative. For vision, we support qwen3-vl:4b and Gemini Vision. For audio, Faster-Whisper extracts timestamped transcripts. "
        "For embeddings, we use sentence-transformers/all-MiniLM-L6-v2 with FlashRank cross-encoder reranking. Finally, for student modeling and verification, we employ Bayesian Knowledge Tracing, "
        "Scikit-Learn Random Forest and Gradient Boosting Regressors, and SymPy for deterministic symbolic verification."
    )

    # =========================================================================
    # SLIDE 5: Spotlight Feature: Quick Diagnostic Baseline Test (User Attached Screenshot!)
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5)
    add_header(s5, "Spotlight Feature: Quick Diagnostic Baseline Test", "COLD-START COGNITIVE CALIBRATION")
    
    # Feature Banner Box (Visual replica of the UI element in user's prompt!)
    banner = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.6), Inches(11.733), Inches(1.15))
    banner.fill.solid()
    banner.fill.fore_color.rgb = RGBColor(24, 18, 12)  # Dark amber tint
    banner.line.color.rgb = COLOR_AMBER
    banner.line.width = Pt(1.5)
    btf = banner.text_frame
    btf.margin_left = Inches(0.4)
    btf.margin_top = Inches(0.2)
    bp1 = btf.paragraphs[0]
    bp1.text = "✨  Quick Diagnostic Baseline Test"
    bp1.font.name = FONT_HEADING
    bp1.font.size = Pt(18)
    bp1.font.bold = True
    bp1.font.color.rgb = COLOR_WHITE
    bp2 = btf.add_paragraph()
    bp2.text = "Tests fundamental concepts across the course to quickly establish your current level."
    bp2.font.name = FONT_BODY
    bp2.font.size = Pt(13)
    bp2.font.color.rgb = COLOR_SLATE_200

    # 3 Strategic Cards Below
    card_w = Inches(3.75)
    card_gap = Inches(0.24)
    top_c = Inches(3.0)
    h_c = Inches(3.8)
    
    # Card 1: The Problem it Solves
    add_card(s5, Inches(0.8), top_c, card_w, h_c)
    tb = s5.shapes.add_textbox(Inches(1.0), top_c + Inches(0.2), card_w - Inches(0.4), h_c - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "1. Cold-Start Problem"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_CYAN
    p.space_after = Pt(10)
    add_bullet(tf, "The Dilemma", "When a new student enters a course, the AI has zero interaction data.", pt_size=12)
    add_bullet(tf, "Standard Failure", "Generic tutors start with basic trivia or assume intermediate knowledge, wasting student time.", pt_size=12)
    add_bullet(tf, "Synapse Solution", "A streamlined 5-question baseline across foundational syllabus milestones.", pt_size=12)

    # Card 2: Algorithmic Mechanics
    add_card(s5, Inches(0.8) + (card_w + card_gap), top_c, card_w, h_c)
    tb = s5.shapes.add_textbox(Inches(1.0) + (card_w + card_gap), top_c + Inches(0.2), card_w - Inches(0.4), h_c - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "2. Adaptive Calibration"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_AMBER
    p.space_after = Pt(10)
    add_bullet(tf, "Topic Sampling", "Algorithm selects root prerequisite topics from the course prerequisite graph.", pt_size=12)
    add_bullet(tf, "Prior P(L0) Tuning", "Correct/incorrect responses adjust initial BKT prior from default 0.15 to student's true entry level.", pt_size=12)
    add_bullet(tf, "Instant Baseline", "Generates initial readiness scores across all course chapters in under 2 minutes.", pt_size=12)

    # Card 3: Downstream Impact
    add_card(s5, Inches(0.8) + (card_w + card_gap)*2, top_c, card_w, h_c)
    tb = s5.shapes.add_textbox(Inches(1.0) + (card_w + card_gap)*2, top_c + Inches(0.2), card_w - Inches(0.4), h_c - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "3. Downstream Benefits"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN
    p.space_after = Pt(10)
    add_bullet(tf, "Personalized Pacing", "Tutor immediately skips mastered basics and focuses directly on conceptual weak zones.", pt_size=12)
    add_bullet(tf, "Scikit-Learn Seeding", "Provides feature vectors for Random Forest readiness and Gradient Boosting time regression.", pt_size=12)
    add_bullet(tf, "Learner Confidence", "Students receive instant clarity on their exact syllabus standing.", pt_size=12)

    set_speaker_notes(s5, 
        "Sir, as shown in the screenshot from our live frontend, the 'Quick Diagnostic Baseline Test' is a critical feature. "
        "In educational data mining, the 'cold-start problem' is notorious. Rather than asking a student 20 tedious onboarding questions, "
        "our diagnostic test samples fundamental nodes from the course prerequisite graph. In under 2 minutes, it calibrates the student's Bayesian Knowledge Tracing prior, "
        "allowing the tutor to tailor subsequent chat explanations and quizzes to their exact cognitive level."
    )

    # =========================================================================
    # SLIDE 6: Cognitive Learner Model & Bayesian Knowledge Tracing (BKT)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6)
    add_header(s6, "Cognitive Modeling: Bayesian Knowledge Tracing & ML")
    
    # Left Card: BKT Mathematical Engine
    add_card(s6, Inches(0.8), Inches(1.7), Inches(5.7), Inches(5.1))
    tb_bkt = s6.shapes.add_textbox(Inches(1.1), Inches(1.9), Inches(5.1), Inches(4.7))
    tf_bkt = tb_bkt.text_frame
    tf_bkt.word_wrap = True
    p = tf_bkt.paragraphs[0]
    p.text = "Bayesian Knowledge Tracing (BKT)"
    p.font.name = FONT_HEADING
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_CYAN
    p.space_after = Pt(12)
    
    add_bullet(tf_bkt, "Novice Prior Initialization", "Initializes mastery at P(L0) = 0.15 (or calibrated via Diagnostic Test).", pt_size=12)
    add_bullet(tf_bkt, "Bayesian Posterior Updating", 
               "Updates mastery given evidence using Slip P(S)=0.10, Guess P(G)=0.20, and Learn Transition P(T)=0.15:\n"
               "P(L_t | Correct) = [P(L_t) * (1 - P(S))] / [P(L_t)*(1 - P(S)) + (1 - P(L_t))*P(G)]", 
               pt_size=11)
    add_bullet(tf_bkt, "Evidence Interaction Weighting", "Differentiates signal confidence: Exam Quiz = 1.0, Short Answer = 0.7, Chat Dialogue Turn = 0.3.", pt_size=12)
    add_bullet(tf_bkt, "Ebbinghaus Forgetting Curve", "Applies exponential half-life decay P(L) = P(L) * e^(-decay * delta_t) over days without practice.", pt_size=12)

    # Right Card: Scikit-Learn Classifiers
    add_card(s6, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.1))
    tb_ml = s6.shapes.add_textbox(Inches(7.1), Inches(1.9), Inches(5.1), Inches(4.7))
    tf_ml = tb_ml.text_frame
    tf_ml.word_wrap = True
    p = tf_ml.paragraphs[0]
    p.text = "Scikit-Learn Machine Learning Models"
    p.font.name = FONT_HEADING
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_AMBER
    p.space_after = Pt(12)
    
    add_bullet(tf_ml, "Random Forest Classifier", 
               "Predicts pedagogical readiness state:\n"
               "• ready_for_next (Mastery >= 0.75 & prerequisites met)\n"
               "• needs_practice (Mastery between 0.40 and 0.75)\n"
               "• prerequisite_gap (Foundational dependencies unmastered)", 
               pt_size=12)
    add_bullet(tf_ml, "Gradient Boosting Regressor (GBR)", 
               "Predicts estimated study minutes required for the student to achieve the 80% mastery target based on historical response accuracy.", 
               pt_size=12)
    add_bullet(tf_ml, "Misconception Diagnosis", "Identifies recurring distractor patterns (e.g. Deadlock State vs Unsafe State confusion) and flags them for remediation.", pt_size=12)

    set_speaker_notes(s6, 
        "Sir, this slide details our cognitive mathematics. We implemented Bayesian Knowledge Tracing with slip, guess, and transition parameters. "
        "Unlike naive counters, our BKT engine weights evidence: a formal quiz question counts for 1.0, while a chat response counts for 0.3. "
        "We also apply Ebbinghaus forgetting decay when days elapse. On top of BKT, we train a Scikit-Learn Random Forest Classifier to assign students into "
        "'ready for next', 'needs practice', or 'prerequisite gap', and a Gradient Boosting Regressor to forecast required study minutes."
    )

    # =========================================================================
    # SLIDE 7: Multimodal Ingestion & Canonical Source Anchoring
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_background(s7)
    add_header(s7, "Multimodal Ingestion & Canonical Source Anchoring")
    
    col_w = Inches(3.75)
    gap = Inches(0.24)
    top_pos = Inches(1.7)
    h_pos = Inches(5.1)
    
    # Card 1: Ingestion Processors
    add_card(s7, Inches(0.8), top_pos, col_w, h_pos)
    tb = s7.shapes.add_textbox(Inches(1.0), top_pos + Inches(0.2), col_w - Inches(0.4), h_pos - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "1. Multimodal Extractors"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_CYAN
    p.space_after = Pt(10)
    add_bullet(tf, "PDF Textbooks", "PyMuPDF extracts text blocks, markdown tables, LaTeX equations, and bounding boxes.", pt_size=11)
    add_bullet(tf, "PowerPoint Slides", "python-pptx extracts slide titles, hierarchical bullet points, tables, and speaker notes.", pt_size=11)
    add_bullet(tf, "Lecture Audio/Video", "Faster-Whisper and youtube-transcript-api generate timestamped transcripts (MM:SS).", pt_size=11)
    add_bullet(tf, "Diagram Vision", "qwen3-vl / Gemini Vision models extract relationships and entity diagrams from slide figures.", pt_size=11)

    # Card 2: Canonical Anchoring
    add_card(s7, Inches(0.8) + (col_w + gap), top_pos, col_w, h_pos)
    tb = s7.shapes.add_textbox(Inches(1.0) + (col_w + gap), top_pos + Inches(0.2), col_w - Inches(0.4), h_pos - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "2. Immutable Anchors"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_AMBER
    p.space_after = Pt(10)
    add_bullet(tf, "Zero Fake Citations", "Every single indexed chunk retains its physical origin metadata in ChromaDB.", pt_size=11)
    add_bullet(tf, "Granular Coordinates", "Chunks anchored with tags:\n• [Source: Module 2 • Slide 18]\n• [Source: Operating Systems • Page 340]\n• [Source: Lecture 4 • 24:15]", pt_size=11)
    add_bullet(tf, "Integrity Verification", "Responses must cite verified anchors; hallucinated citations are automatically stripped.", pt_size=11)

    # Card 3: Interactive Source Viewer Drawer
    add_card(s7, Inches(0.8) + (col_w + gap)*2, top_pos, col_w, h_pos)
    tb = s7.shapes.add_textbox(Inches(1.0) + (col_w + gap)*2, top_pos + Inches(0.2), col_w - Inches(0.4), h_pos - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "3. Source Viewer Drawer"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN
    p.space_after = Pt(10)
    add_bullet(tf, "Slide-Over Drawer", "Clicking any citation chip in the chat dynamically opens the slide-over source drawer.", pt_size=11)
    add_bullet(tf, "Direct Jump", "Opens the exact PDF page, PPTX slide image, or video segment without leaving the chat.", pt_size=11)
    add_bullet(tf, "Student Trust", "Students can verify the AI's explanation against the professor's exact words in 1 click.", pt_size=11)

    set_speaker_notes(s7, 
        "Sir, academic credibility requires canonical source anchoring. We ingest PDFs using PyMuPDF, slide decks using python-pptx, and lecture videos using Faster-Whisper. "
        "Every knowledge chunk carries immutable metadata. When the tutor answers, it outputs clickable citation chips. Clicking a badge opens our frontend "
        "Source Viewer Drawer, jumping directly to the exact page, slide, or video timestamp."
    )

    # =========================================================================
    # SLIDE 8: Grounded Hybrid RAG & Strict Refusal Benchmark
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_background(s8)
    add_header(s8, "Hybrid Grounded RAG & Strict Off-Material Refusal")
    
    # Left Card: Hybrid Retrieval Pipeline
    add_card(s8, Inches(0.8), Inches(1.7), Inches(5.7), Inches(5.1))
    tb_rag = s8.shapes.add_textbox(Inches(1.1), Inches(1.9), Inches(5.1), Inches(4.7))
    tf_rag = tb_rag.text_frame
    tf_rag.word_wrap = True
    p = tf_rag.paragraphs[0]
    p.text = "Hybrid Grounded Retrieval Pipeline"
    p.font.name = FONT_HEADING
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_CYAN
    p.space_after = Pt(12)
    
    add_bullet(tf_rag, "Multi-Turn Contextualization", "Rewrites ambiguous follow-up prompts (e.g. 'Can you give an example calculation?') using sliding conversation context.", pt_size=12)
    add_bullet(tf_rag, "all-MiniLM-L6-v2 Dense Search", "Dense vector embeddings capture semantic intent and broad conceptual similarity in ChromaDB.", pt_size=12)
    add_bullet(tf_rag, "BM25 Lexical Keyword Matching", "Catches exact technical acronyms, API function names, and mathematical equations missed by dense search.", pt_size=12)
    add_bullet(tf_rag, "FlashRank Cross-Encoder Reranking", "Scores dense + sparse candidates with cross-attention to select top 3 most relevant passages.", pt_size=12)

    # Right Card: Strict Refusal & Section 37 Benchmark
    add_card(s8, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.1))
    tb_ref = s8.shapes.add_textbox(Inches(7.1), Inches(1.9), Inches(5.1), Inches(4.7))
    tf_ref = tb_ref.text_frame
    tf_ref.word_wrap = True
    p = tf_ref.paragraphs[0]
    p.text = "Section 37 Off-Material Benchmark"
    p.font.name = FONT_HEADING
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_AMBER
    p.space_after = Pt(12)
    
    add_bullet(tf_ref, "Zero Hallucination Policy", "If an inquiry asks for out-of-syllabus concepts (e.g., asking for chocolate cake recipes or GPU architectures in an OS course), the system strictly refuses.", pt_size=12)
    add_bullet(tf_ref, "Standardized Refusal Message", "'This topic is not covered in the uploaded course material.'", title_color=RGBColor(252, 165, 165), pt_size=12)
    add_bullet(tf_ref, "Opt-In Outside Knowledge", "The tutor offers an explicit 'Explain with Outside Knowledge' toggle, clearly labeled so students know it is external.", pt_size=12)
    add_bullet(tf_ref, "100% Benchmark Score", "Tested across 5 adversarial out-of-syllabus queries in scripts/run_evaluation: 5/5 (100.0%) refusal accuracy.", title_color=COLOR_GREEN, pt_size=12)

    set_speaker_notes(s8, 
        "Sir, grounded RAG in an educational setting cannot simply be dense search. We combine dense embeddings with BM25 lexical keyword search, followed by FlashRank cross-encoder reranking. "
        "More importantly, we enforce a strict off-material refusal policy: if a student asks questions not present in the course syllabus, the tutor refuses with 100% accuracy, "
        "offering an opt-in toggle if they explicitly want external general knowledge."
    )

    # =========================================================================
    # SLIDE 9: Self-Verifying Adaptive Assessment Engine
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_background(s9)
    add_header(s9, "Self-Verifying Adaptive Assessment Engine")
    
    col_w = Inches(3.75)
    gap = Inches(0.24)
    top_pos = Inches(1.7)
    h_pos = Inches(5.1)
    
    # Card 1: Adaptive Selection Distribution
    add_card(s9, Inches(0.8), top_pos, col_w, h_pos)
    tb = s9.shapes.add_textbox(Inches(1.0), top_pos + Inches(0.2), col_w - Inches(0.4), h_pos - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "1. Adaptive 50/30/20"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_CYAN
    p.space_after = Pt(10)
    add_bullet(tf, "50% Weak Concepts", "P(L) < 0.50 — Targets high-priority cognitive deficits where student needs scaffolding.", pt_size=11)
    add_bullet(tf, "30% Intermediate", "0.50 <= P(L) < 0.75 — Builds retention on emerging concepts.", pt_size=11)
    add_bullet(tf, "20% Review Mastery", "P(L) >= 0.75 — Reinforces mastered skills to prevent Ebbinghaus forgetting decay.", pt_size=11)
    add_bullet(tf, "Diagnostic Mode", "Cold-start foundational pre-test for brand new courses.", pt_size=11)

    # Card 2: SymPy Deterministic Math Verifier
    add_card(s9, Inches(0.8) + (col_w + gap), top_pos, col_w, h_pos)
    tb = s9.shapes.add_textbox(Inches(1.0) + (col_w + gap), top_pos + Inches(0.2), col_w - Inches(0.4), h_pos - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "2. SymPy Math Verifier"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_AMBER
    p.space_after = Pt(10)
    add_bullet(tf, "Generator Pipeline", "LLM generates question, correct solution, explanation, and 3 distractors.", pt_size=11)
    add_bullet(tf, "Deterministic Symbolic Check", "SymPy library symbolically solves mathematical questions to ensure the target answer is mathematically true.", pt_size=11)
    add_bullet(tf, "Distractor Collision Check", "Verifies no duplicate distractors and confirms distractors are mathematically distinct from correct answer.", pt_size=11)

    # Card 3: Novelty Checker & Misconceptions
    add_card(s9, Inches(0.8) + (col_w + gap)*2, top_pos, col_w, h_pos)
    tb = s9.shapes.add_textbox(Inches(1.0) + (col_w + gap)*2, top_pos + Inches(0.2), col_w - Inches(0.4), h_pos - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "3. Novelty & Remediation"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN
    p.space_after = Pt(10)
    add_bullet(tf, "Cosine Novelty Checker", "Computes all-MiniLM-L6-v2 dense embedding cosine similarity against all previously asked questions.", pt_size=11)
    add_bullet(tf, "0% Question Repetition", "Rejects any generated question with similarity > 0.85, guaranteeing zero repeats.", pt_size=11)
    add_bullet(tf, "Misconception Diagnosis", "Maps chosen wrong answers to specific conceptual errors and injects remediation guidance.", pt_size=11)

    set_speaker_notes(s9, 
        "Sir, for our assessment engine, questions are not picked randomly. We use a 50/30/20 adaptive sampling policy targeting 50% weak concepts, 30% intermediate, and 20% review. "
        "Furthermore, we implement self-verification: mathematical questions are passed through Python's SymPy library for symbolic validation, "
        "and our novelty checker embeds past questions with MiniLM-L6-v2 to ensure cosine similarity never exceeds 0.85, yielding a 100% novelty pass rate."
    )

    # =========================================================================
    # SLIDE 10: Three-Tier Cognitive Memory Architecture
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_background(s10)
    add_header(s10, "Three-Tier Cognitive Memory Architecture")
    
    col_w = Inches(3.75)
    gap = Inches(0.24)
    top_pos = Inches(1.7)
    h_pos = Inches(5.1)
    
    # Tier 1: Short-Term
    add_card(s10, Inches(0.8), top_pos, col_w, h_pos)
    tb = s10.shapes.add_textbox(Inches(1.0), top_pos + Inches(0.2), col_w - Inches(0.4), h_pos - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "TIER 1\nShort-Term Memory"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_CYAN
    p.space_after = Pt(10)
    add_bullet(tf, "Sliding Dialogue Window", "Maintains active session dialogue turns for conversational coherence.", pt_size=11)
    add_bullet(tf, "Query Disambiguation", "Resolves anaphoric references ('what was that algorithm again?') to the active topic.", pt_size=11)
    add_bullet(tf, "Session Scaffolding", "Tracks whether the current turn needs step-by-step guidance or quick confirmation.", pt_size=11)

    # Tier 2: Long-Term
    add_card(s10, Inches(0.8) + (col_w + gap), top_pos, col_w, h_pos)
    tb = s10.shapes.add_textbox(Inches(1.0) + (col_w + gap), top_pos + Inches(0.2), col_w - Inches(0.4), h_pos - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "TIER 2\nLong-Term Profile"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_AMBER
    p.space_after = Pt(10)
    add_bullet(tf, "Relational SQLite State", "Persistent mastery distributions P(L) across all course topics.", pt_size=11)
    add_bullet(tf, "Behavioral Profile", "Tracks explanation preference (analogy first vs formal math first), pacing, and scaffolding level.", pt_size=11)
    add_bullet(tf, "Dynamic Adaptation", "Switches to 'intuitive analogy first' automatically when repeated confusion signals occur.", pt_size=11)

    # Tier 3: Episodic
    add_card(s10, Inches(0.8) + (col_w + gap)*2, top_pos, col_w, h_pos)
    tb = s10.shapes.add_textbox(Inches(1.0) + (col_w + gap)*2, top_pos + Inches(0.2), col_w - Inches(0.4), h_pos - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "TIER 3\nEpisodic Memory"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN
    p.space_after = Pt(10)
    add_bullet(tf, "Milestone Timeline", "Chronological records of critical learning events: confusion, breakthroughs, and misconceptions.", pt_size=11)
    add_bullet(tf, "Prompt Injection", "Future tutor prompts inject past episodic struggles: 'Recall how we resolved Banker's algorithm last Tuesday?'", pt_size=11)
    add_bullet(tf, "Metacognitive Growth", "Empowers the student by referencing their own demonstrated progress over time.", pt_size=11)

    set_speaker_notes(s10, 
        "Sir, our memory system is modeled after cognitive science with three distinct tiers: Short-term memory holds active conversational dialogue. "
        "Long-term memory stores relational database mastery profiles and learning styles in SQLite. "
        "Episodic memory logs specific breakthrough moments and misconceptions over time, allowing the tutor to reference past learning milestones in future sessions."
    )

    # =========================================================================
    # SLIDE 11: Technical Implementation & Engineering Fixes
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    set_slide_background(s11)
    add_header(s11, "Technical Engineering Highlights & Problem-Solving")
    
    # Left Card: Technology Stack
    add_card(s11, Inches(0.8), Inches(1.7), Inches(5.7), Inches(5.1))
    tb_tech = s11.shapes.add_textbox(Inches(1.1), Inches(1.9), Inches(5.1), Inches(4.7))
    tf_tech = tb_tech.text_frame
    tf_tech.word_wrap = True
    p = tf_tech.paragraphs[0]
    p.text = "Production Technology Stack"
    p.font.name = FONT_HEADING
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_CYAN
    p.space_after = Pt(12)
    add_bullet(tf_tech, "Backend", "FastAPI (Async Python 3.13), AsyncSQLAlchemy, SQLite WAL mode.", pt_size=12)
    add_bullet(tf_tech, "Frontend", "React 19, TypeScript, Vite, Tailwind CSS, KaTeX math typesetting.", pt_size=12)
    add_bullet(tf_tech, "Local LLM Runtime", "Ollama daemon running qwen2.5:7b on NVIDIA RTX GPU (CUDA acceleration).", pt_size=12)
    add_bullet(tf_tech, "Retrieval & Vectors", "ChromaDB embedded vector database, all-MiniLM-L6-v2 embeddings, FlashRank reranker.", pt_size=12)
    add_bullet(tf_tech, "Data Ingestion", "PyMuPDF, python-pptx, Faster-Whisper, SymPy.", pt_size=12)

    # Right Card: Real-world Engineering Fixes
    add_card(s11, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.1))
    tb_eng = s11.shapes.add_textbox(Inches(7.1), Inches(1.9), Inches(5.1), Inches(4.7))
    tf_eng = tb_eng.text_frame
    tf_eng.word_wrap = True
    p = tf_eng.paragraphs[0]
    p.text = "Engineering Issues Resolved"
    p.font.name = FONT_HEADING
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_AMBER
    p.space_after = Pt(12)
    add_bullet(tf_eng, "Resilient LLM Auto-Fallback", "Added robust try/except fallback logic so offline AI endpoints gracefully fall back to MockLLM without crashing HTTP 500.", pt_size=12)
    add_bullet(tf_eng, "KaTeX Math Rendering", "Upgraded regex tokenizers in FormattedMessage.tsx to parse LaTeX delimiters \\(...\\) and \\[...\\] into clean rendered math.", pt_size=12)
    add_bullet(tf_eng, "Windows Execution Policy", "Resolved PowerShell npm.ps1 restrictions by using npm.cmd to ensure reliable frontend startup.", pt_size=12)
    add_bullet(tf_eng, "UI Streamlining", "Consolidated navigation from 7 tabs to 5 focused views (Dashboard, Tutor, Tests, Courses, Profile).", pt_size=12)

    set_speaker_notes(s11, 
        "Sir, during development we resolved several critical engineering challenges: we configured Ollama qwen2.5:7b with local CUDA GPU acceleration on our NVIDIA RTX card. "
        "We built resilient try/catch auto-fallbacks so the application never crashes if an AI endpoint is unreachable. We fixed KaTeX LaTeX delimiter rendering in React, "
        "and streamlined the user interface into 5 high-impact workspaces."
    )

    # =========================================================================
    # SLIDE 12: Benchmark Results & Live Demo
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    set_slide_background(s12)
    add_header(s12, "Evaluation Benchmarks & Live Demo Verification")
    
    # 4 Metric Cards Across
    m_w = Inches(2.75)
    m_gap = Inches(0.24)
    m_top = Inches(1.7)
    m_h = Inches(2.3)
    
    metrics = [
        ("100.0%", "Off-Material Refusal", "Section 37 benchmark: 5/5 out-of-syllabus questions strictly rejected.", COLOR_CYAN),
        ("100.0%", "Citation Grounding", "Zero unanchored statements; all facts point to verified slides/pages.", COLOR_GREEN),
        ("100.0%", "Question Novelty", "Zero repetition; MiniLM dense cosine similarity threshold < 0.85 enforced.", COLOR_AMBER),
        ("+95.0%", "BKT Learning Gain", "Simulated learner trajectory mastery increased from 0.15 to 0.95.", COLOR_PURPLE),
    ]
    
    for i, (val, title, desc, col) in enumerate(metrics):
        x = Inches(0.8) + (m_w + m_gap) * i
        add_card(s12, x, m_top, m_w, m_h)
        tb = s12.shapes.add_textbox(x + Inches(0.15), m_top + Inches(0.15), m_w - Inches(0.3), m_h - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = val
        p.font.name = FONT_HEADING
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = col
        p.space_after = Pt(2)
        
        p2 = tf.add_paragraph()
        p2.text = title
        p2.font.name = FONT_HEADING
        p2.font.size = Pt(13)
        p2.font.bold = True
        p2.font.color.rgb = COLOR_WHITE
        p2.space_after = Pt(4)
        
        p3 = tf.add_paragraph()
        p3.text = desc
        p3.font.name = FONT_BODY
        p3.font.size = Pt(10)
        p3.font.color.rgb = COLOR_SLATE_400

    # Live Demo Container Below
    add_card(s12, Inches(0.8), Inches(4.3), Inches(11.733), Inches(2.5))
    tb_demo = s12.shapes.add_textbox(Inches(1.1), Inches(4.5), Inches(11.1), Inches(2.1))
    tf_demo = tb_demo.text_frame
    tf_demo.word_wrap = True
    
    p = tf_demo.paragraphs[0]
    p.text = "Live Demonstration Workflow"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_CYAN
    p.space_after = Pt(8)
    
    add_bullet(tf_demo, "Step 1: Course Onboarding", "Upload syllabus materials (PDF / PPTX / Video) or select sample Operating Systems course.", pt_size=11)
    add_bullet(tf_demo, "Step 2: Quick Diagnostic Baseline", "Demonstrate cold-start calibration to establish baseline BKT mastery in under 2 minutes.", pt_size=11)
    add_bullet(tf_demo, "Step 3: Grounded Tutor Chat", "Ask technical questions with KaTeX math rendering and click citation badges to open the Source Viewer Drawer.", pt_size=11)
    add_bullet(tf_demo, "Step 4: Self-Verifying Adaptive Assessment", "Take an adaptive quiz with real-time BKT updates and Scikit-Learn readiness recalculation.", pt_size=11)

    set_speaker_notes(s12, 
        "Sir, our evaluation benchmarks run automated scripts verifying our architectural guarantees: 100% off-material refusal accuracy, 100% citation grounding, "
        "100% question novelty rate, and +95% simulated BKT learning gain. Both backend and frontend are live, and we can immediately proceed into the live software demonstration."
    )

    # =========================================================================
    # SLIDE 13: Conclusion & Internship Takeaways
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    set_slide_background(s13)
    add_header(s13, "Summary, Internship Learnings & Next Steps")
    
    # Left Card: Core Takeaways
    add_card(s13, Inches(0.8), Inches(1.7), Inches(5.7), Inches(5.1))
    tb_sum = s13.shapes.add_textbox(Inches(1.1), Inches(1.9), Inches(5.1), Inches(4.7))
    tf_sum = tb_sum.text_frame
    tf_sum.word_wrap = True
    p = tf_sum.paragraphs[0]
    p.text = "Key Internship Achievements"
    p.font.name = FONT_HEADING
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_CYAN
    p.space_after = Pt(12)
    add_bullet(tf_sum, "Cognitive Over Generative", "Proved that true educational AI requires mathematical learner modeling (BKT + ML), not just raw LLM prompts.", pt_size=12)
    add_bullet(tf_sum, "Full-Stack System Engineering", "Built a production-grade decoupled architecture spanning React 19, FastAPI, ChromaDB, and SQLite WAL.", pt_size=12)
    add_bullet(tf_sum, "Local GPU Deployment", "Integrated local Ollama 7B LLM running directly on hardware GPU with zero cloud token dependency.", pt_size=12)
    add_bullet(tf_sum, "Deterministic Verification", "Guaranteed academic rigor using SymPy math verifier and cosine novelty detection.", pt_size=12)

    # Right Card: Next Steps & Q&A
    add_card(s13, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.1))
    tb_qa = s13.shapes.add_textbox(Inches(7.1), Inches(1.9), Inches(5.1), Inches(4.7))
    tf_qa = tb_qa.text_frame
    tf_qa.word_wrap = True
    p = tf_qa.paragraphs[0]
    p.text = "Future Extensions & Thank You"
    p.font.name = FONT_HEADING
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN
    p.space_after = Pt(12)
    add_bullet(tf_qa, "Multimodal Speech Interaction", "Add real-time bidirectional voice tutoring using WebRTC and local Whisper + VITS.", pt_size=12)
    add_bullet(tf_qa, "Collaborative Peer Study Rooms", "Extend cognitive tracing to multi-student peer problem-solving sessions.", pt_size=12)
    add_bullet(tf_qa, "LMS Canvas / Moodle Integration", "Export student mastery distributions and readiness states directly into university gradebooks.", pt_size=12)
    
    p_thank = tf_qa.add_paragraph()
    p_thank.space_before = Pt(20)
    p_thank.text = "Thank You, Sir!\nOpen for Questions & Live Demonstration."
    p_thank.font.name = FONT_HEADING
    p_thank.font.size = Pt(16)
    p_thank.font.bold = True
    p_thank.font.color.rgb = COLOR_WHITE

    set_speaker_notes(s13, 
        "Thank you, Sir! In summary, SynapseTutor demonstrates that combining cognitive models with modern local LLMs creates a far more reliable, trustworthy, "
        "and personalized learning experience. I am now ready to walk you through the live demo and answer any technical questions."
    )

    # Save Presentation
    output_filename_v2 = "SynapseTutor_AI_Presentation_v2.pptx"
    prs.save(output_filename_v2)
    print(f"Presentation saved to: {os.path.abspath(output_filename_v2)}")

    output_filename = "SynapseTutor_AI_Internship_Presentation.pptx"
    try:
        prs.save(output_filename)
        print(f"Presentation successfully updated: {os.path.abspath(output_filename)}")
    except PermissionError:
        print(f"Note: {output_filename} is currently open in PowerPoint. Saved as {output_filename_v2}!")

if __name__ == "__main__":
    build_presentation()
