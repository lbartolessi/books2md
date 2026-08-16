# **Unified Global Orthotypographic Standard for AI-Ready Markdown**

## **Structural Context of Books2MD**

The transition from complex academic and philosophical EPUB source documents to "Semantic Gold" Markdown requires an orthotypographic standard designed for a dual audience: human readers who demand typographic elegance, and Large Language Model (LLM) or Retrieval-Augmented Generation (RAG) systems that require high signal-to-noise ratios.1 Modern NLP engines do not process text in the holistic manner of human eyes; instead, they rely on subword tokenizers that map character sequences into mathematical vector spaces.2 Typographic inconsistencies—such as ambiguous dashes, mismatched quotation marks, non-standard whitespace, and erratic punctuation placement—fragment word tokens, inflate vocabulary costs, and distort semantic embedding similarity calculations.3  
By analyzing the intersections of international standards, including the Chicago Manual of Style (CMOS), DIN 5008, the Real Academia Española (RAE/ASALE), and the International Organization for Standardization (ISO 8601), this standard establishes a unified orthotypographic framework. This framework treats punctuation as functional syntax, minimizing tokenizer boundary errors while preserving human readability.

## **Dashes and Tokenization Dynamics**

### **The Structural Bias and Origin of the Em-Dash**

In instruction-tuned language models, the over-generation of em-dashes (—) has emerged as a distinct indicator of machine-generated prose.6 This phenomenon is a direct consequence of training data composition.6 The corpora used to train state-of-the-art models are saturated with Markdown-formatted text from developer platforms, project documentation, and online forums where horizontal dashes—such as horizontal rules (---), list markers (-), and front-matter delimiters—are used to establish structural boundaries rather than literary transitions.6  
Language models internalize this structural orientation, treating the dash as a architectural marker representing the end of one semantic unit and the beginning of another.6 Because the em-dash occupies a dual-register position—functioning both as valid prose punctuation and as a Markdown structural indicator—it survives post-training safety and formatting filters.6 It represents a "last fingerprint" of Markdown structure leaking into generated prose.6  
Linguistic analysis shows that the historical frequency of em-dashes in human-authored English text has declined from a peak of approximately 0.35% in 1860 to a stable baseline of 0.25% to 0.275% in the late twentieth century.9 In contrast, LLM outputs exhibit a high density of em-dashes, using them as versatile, safe transitions to avoid committing to terminal punctuation.9 To restore narrative elegance and align with modern typographic practices, a systematic transition is required.

### **The Spaced En-Dash as a Typographic Alternative**

Modern typographic standards reject the Victorian, close-set em-dash, arguing that it is too long for high-quality text faces and disrupts the even texture of a page.10 It introduces excessive visual tension between the ends of the dash and the adjacent characters.11 This standard adopts the recommendation of Robert Bringhurst’s *The Elements of Typographic Style*, which advocates for the spaced en-dash ( – ) as the standard marker for parenthetical insertions and sentence-level breaks.10  
The spaced en-dash provides a clean, balanced visual break for human readers while preventing character-clumping in subword tokenizers.4 When an em-dash is set close (e.g., word—word), standard tokenizers such as Byte-Pair Encoding (BPE) or WordPiece often fail to split the sequence cleanly, binding the punctuation to the surrounding words and generating rare, out-of-vocabulary tokens that increase computational costs and degrade semantic vector quality.1 Spacing the en-dash with standard spaces (–) ensures that the punctuation mark is isolated as an independent token, preserving the morphological integrity of the adjacent words.3

### **DIN 5008, Duden, and Numeric Spans**

A major orthographic conflict exists between German national standards regarding the "bis" (to/through) dash.14 The DIN 5008 standard, which governs layout and text processing rules in office environments, requires a spaced en-dash to represent ranges (e.g., 10 – 12 or 13:00 – 14:00 Uhr).15 Conversely, the Duden orthographic dictionary rejects this spacing, prescribing an unspaced en-dash (e.g., 10–12 or 13:00–14:00 Uhr).14  
For AI-Ready Markdown, this conflict is resolved in favor of the **Duden** unspaced model for numeric spans.16 Introducing spaces within a numeric range causes SentencePiece and BPE tokenizers to segment the range into three separate, isolated entities (e.g., , \`\[–\]\`, ), complicating pattern-matching algorithms, named entity recognition (NER) models, and mathematical value extractions.3 Keeping the en-dash close-set (e.g., 10–12) ensures that range boundaries are parsed as unified, easily detectable semantic strings.18  
To support both human reading experiences and machine parsing, the standard horizontal line typology is mapped in Table 1\.

| Typographic Element | Unicode Code Point | Markdown Representation | Spacing Constraint | Target Standard Alignment | Tokenizer Processing Behavior |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Hyphen** | U+002D (-) | \- | Unspaced; tight on both sides.20 | ISO 8601, CMOS.22 | Merges with prefixes or compound parts; treated as a single token in common patterns.5 |
| **En-dash (Range)** | U+2013 (–) | \-- | Unspaced; tight on both sides.18 | Duden, CMOS, ASAPS.15 | Preserves the boundary between numeric limits as a single, unfragmented string.18 |
| **Spaced En-dash (Parenthetical)** | U+2013 (–) | \-- | Surrounded by standard spaces ( U+0020).19 | Bringhurst, DIN 5008, British Standard.10 | Tokenizes as a distinct, isolated punctuation token; protects adjacent word morphology.3 |
| **Em-dash (Dialogue/Interruption)** | U+2014 (—) | \--- | Unspaced when clipping; spaced prior to attribution.12 | CMOS, RAE/ASALE.12 | Emitted as a single token; represents sudden narrative termination or speaker changes.29 |
| **3-Em-dash** | U+2014 (×3) | \------ | Unspaced.26 | CMOS Bibliographies (deprecated).26 | Highly inefficient; causes tokenizer fragmentation; must be avoided in Markdown.26 |

## **The Quotation Mark Hierarchy and Parser Canonicalization**

### **Linguistic Tradition vs. Technical Canonicalization**

Linguistic traditions dictate unique quotation systems across different regions.31 English publishing relies on double curly quotes (“ ”) and single curly quotes (‘ ’).33 Spanish and French orthography traditionally favors double angle quotes or guillemets (« »).31  
However, in multilingual RAG pipelines, preserving these localized variations introduces significant noise. It forces text parsers and semantic search systems to maintain duplicate translation sets and complex matching algorithms to handle simple quoted strings.24  
A unified, language-agnostic typographic standard is therefore required to simplify RAG parsing. By establishing a single canonical hierarchy across all processed languages, the Books2MD pipeline ensures that downstream LLMs can extract literal speech, defined terms, and cited titles without language-specific preprocessing overhead.24

### **The Apostrophe Collision Problem**

In English, the standard typographic apostrophe (’ U+2019) is identical to the right single curly quote (’ U+2019).33 In French, the apostrophe is used continuously for elisions (e.g., *l'ensemble*, *d'abord*).24  
If single curly quotes are used as primary or secondary quotation marks, parser scripts and LLM tokenizers struggle to distinguish between a closing quotation mark and a contraction apostrophe.24 This ambiguity leads to parsing failures, where an entire paragraph might be incorrectly identified as a continuous quote because of a mismatched apostrophe token.33  
Using straight quotes (" and ') is equally problematic, as they collide with Markdown code block wrappers, YAML front-matter metadata, and system command syntax.35  
To prevent these errors, the primary quote level is standardized as **Guillemets** (« »).31 Guillemets occupy unique positions in Unicode space, do not exist in standard English prose except as quotes, and have zero probability of colliding with typographic apostrophes or Markdown syntax.24 This separation enforces a strict distinction between quotation boundaries and vocabulary contractions.33  
The standard quotation mark hierarchy is defined in Table 2\.

| Quote Tier | Glyphs | Unicode Code Points | Spacing Rule | Collision Risk with U+2019 / Markdown | Tokenizer Efficiency |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Primary Tier** | « » | U+00AB, U+00BB | Tight to text; zero space.31 | **Zero:** Complete visual and electronic separation.31 | High; easily identified as structural brackets.1 |
| **Secondary Tier** | “ ” | U+201C, U+201D | Tight to text; zero space.33 | **Low:** Distinct from standard apostrophes.33 | High; standard in English pre-training corpora.5 |
| **Tertiary Tier** | ‘ ’ | U+2018, U+2019 | Tight to text; zero space.33 | **High:** Identical to typographic apostrophe.24 | Low; causes fragmentation in contractions.3 |

## **Whitespace, Punctuation Spacing, and Embedding Vector Alignment**

### **The French Space vs. English Tight Debate**

Standard French orthography dictates that double punctuation marks—colons (:), semicolons (;), question marks (?), and exclamation points (\!)—must be preceded by a non-breaking space, while guillemets must be separated from their enclosed text by internal spaces.37 Historically, fine-press typographers utilized the "thin space" (U+2009) or the "narrow no-break space" (U+202F) to achieve this layout.37  
In modern NLP systems, however, these specialized whitespace characters introduce parsing issues.39 For example, the non-reasoning GPT-5 pipeline often inserts U+202F erratically across markdown headers, tables, and prose.39 On operating systems like macOS and iOS, this character frequently fails to render properly, compressing text blocks or displaying them as empty glyph boxes, which degrades readability for human users.39  
For machine readers, non-standard spaces behave as "garbage tokens".40 Modern embedding models rely on L2 normalization and cosine similarity to map semantic vectors onto a unit hypersphere.42  
If a French text incorporates narrow no-break spaces (U+202F) or zero-width non-joiners (U+200C), standard subword algorithms like BPE fragment the adjacent punctuation and root words into rare, fractional tokens.40 This fragmentation changes the token sequence, distorting the coordinates of the resulting embedding vector and lowering the model's semantic similarity score for identical phrases.2  
Therefore, this standard mandates the **English Tight** model across all target languages.39 All punctuation must directly touch the preceding word.31 Layout adjustments can then be handled during final rendering using Pandoc extensions (e.g., \--smart) or CSS style engines.36  
Table 3 establishes the whitespace normalization rules.

| Unicode Space Character | Code Point | Local Orthographic Tradition | LLM Parsing & Rendering Impact | Standardized Action in Markdown |
| :---- | :---- | :---- | :---- | :---- |
| **Standard Space** | U+0020 | Global baseline standard.39 | Standard; dense registration in token vocabularies.5 | **Retain:** Primary word separator.39 |
| **Narrow No-Break Space** | U+202F | French punctuation prefix.37 | Causes text-rendering failures; fragments BPE tokens.39 | **Replace:** Convert to U+0020 or strip before punctuation.39 |
| **Thin Space** | U+2009 | Typography; nesting quotes.38 | Distorts embedding calculations; creates garbage subwords.40 | **Strip:** Remove or replace with standard U+0020.40 |
| **Zero-Width Non-Joiner** | U+200C | Perso-Arabic orthography.40 | Prevents correct token clustering; degrades semantic search.40 | **Strip:** Eliminate in Latin-script markdown conversions.40 |

## **Trailing Punctuation Placement and Logical Integrity**

### **Aesthetic vs. Logical Punctuation**

The traditional American "Aesthetic" punctuation style requires periods and commas to be placed inside quotation marks, regardless of whether they belong to the quoted text.32 Colons and semicolons are placed outside.32 This system is highly inconsistent and presents significant challenges for machine parsing.32  
In contrast, the British "Logical" punctuation style dictates that quotation marks act as strict boundary brackets: punctuation is only placed inside if it was part of the original quoted source.33 Semicolons, colons, and periods that belong to the parent sentence remain outside.32

### **The Philosophical and NLP Rationale**

For systems that process semantic metadata, the logical style is required.34 This approach aligns with the use/mention distinction defined by logicians like Willard Van Orman Quine and Kurt Gödel.34 This distinction argues that the integrity of a quoted literal string must be maintained; a parent sentence must not alter the internal punctuation of a quoted phrase.34  
When a RAG system extracts a defined term from a text, aesthetic punctuation introduces noise (e.g., retrieving the word as "concept," instead of "concept"), which breaks indexing keys, keyword matches, and dictionary lookups.32 Standardizing on the logical style ensures that quoted strings remain clean and uncontaminated by parent sentence punctuation.33  
Table 4 outlines the punctuation placement rules.

| Punctuation Type | Aesthetic Style (Incorrect for AI) | Logical Style (Mandated Standard) | Semantic Parsing / NLP Benefit |
| :---- | :---- | :---- | :---- |
| **Comma (Fragmentary Quote)** | «The term is "magic,"» said the speaker.34 | «The term is "magic"», said the speaker.34 | Isolates the literal string "magic" cleanly for extraction and indexing.33 |
| **Period (Fragmentary Quote)** | She described it as "absolute magic." 34 | She described it as "absolute magic". 34 | Prevents the period from corrupting the lookup value of the term.32 |
| **Period (Complete Sentence)** | He said, "The game is over." 32 | He said, "The game is over." 32 | Correctly shows that the quoted text is a complete, self-contained sentence.32 |
| **Semicolon / Colon** | Always placed outside quotes.32 | Always placed outside quotes.32 | Consistent with the logical boundary of the quote.32 |
| **Question / Exclamation** | Inside or outside depending on context.32 | Inside or outside depending on context.32 | Standardizes semantic intent (e.g., whether the quote itself is a question).48 |

## **Dash Interactions at Sentence Boundaries**

When parenthetical insertions or speech interruptions occur at sentence boundaries, the interaction of the dash with terminal punctuation is governed by specific cross-linguistic rules:

### **The English Swallowing Protocol**

Under CMOS guidelines, when a parenthetical break marked by a spaced en-dash occurs at the end of an English sentence, the closing en-dash is swallowed by the terminal period.27 It is incorrect to place a dash directly before a period.27 For dialogue interruptions, the em-dash is placed inside the quotation marks, and all terminal punctuation is omitted.29

### **The Spanish and French Non-Swallowing Protocol**

Linguistic authorities for Spanish (RAE/ASALE) and French reject the English swallowing protocol.28 In these languages, the parenthetical closing dash (raya de cierre) is a mandatory structural bracket that cannot be omitted.28 The closing dash must be written, followed immediately by the terminal punctuation of the sentence (e.g., —. or —,).28  
This ensures that the parenthetical phrase is cleanly bounded on both sides, allowing parsing engines to accurately identify the parenthetical insertion as a complete block.28  
Table 5 defines the cross-linguistic protocols for dash-punctuation interactions.

| Language | Parenthetical Sentence-End Protocol | Dialogue Interruption Protocol | Parser Parsing Logic |
| :---- | :---- | :---- | :---- |
| **English** | The dash is swallowed: word – word. 27 | The dash is set close with no period: «word—».29 | Recognizes sentence termination via standard period; parses the final clause as part of the main sentence.27 |
| **Spanish** | The dash is retained: word —word—. 28 | The dash is set close with no period: —word—.29 | Identifies parenthetical blocks using symmetrical dash boundaries.28 |
| **French** | The dash is retained: word —word—. 28 | The dash is set close with no period: —word—.29 | Symmetrical boundary parsing; ensures matching counts of open/close dashes.28 |

## **Comparative Examples for English, Spanish, and French**

The following examples demonstrate the transformation of legacy, unformatted, or traditionally formatted texts into Unified AI-Ready Gold Markdown.

### **English Transformations**

#### **Parenthetical Spacing and Logical Punctuation**

* **Before (Legacy/Aesthetic):**  
  The author’s primary thesis—which he outlines in chapter 4—is that "the medium itself is the message," but this is often misunderstood.  
* **After (Unified AI-Ready):** The author’s primary thesis – which he outlines in chapter 4 – is that «the medium itself is the message», but this is often misunderstood.26

#### **Numeric Spans, Dates, and Hierarchy**

* **Before (Legacy/Aesthetic):**  
  He served as the director from 1995-1999. His lecture on “The ‘Neoliberal’ Consensus” took place on 06/07/2026.  
* **After (Unified AI-Ready):** He served as the director from 1995 to 1999\.18 His lecture on «The “Neoliberal” Consensus» took place on 2026-06-07.23

#### **English Dash Swallowing**

* **Before (Legacy/Aesthetic):**  
  He had only one goal left—to survive—.  
* **After (Unified AI-Ready):** He had only one goal left – to survive.27

### **Spanish Transformations**

#### **Dialogue and Quote Hierarchy**

* **Before (Legacy/Aesthetic):**  
  —¿Dónde vas? —preguntó Juan—. “He decidido irme a la playa”, respondió ella.  
* **After (Unified AI-Ready):** —¿Dónde vas? —preguntó Juan—. «He decidido irme a la playa», respondió ella.29

#### **Spanish Non-Swallowing Dash**

* **Before (Legacy/Aesthetic):**  
  La automatización puede producir un desplazamiento de mano de obra—el resultado común que ha de evitarse.  
* **After (Unified AI-Ready):** La automatización puede producir un desplazamiento de mano de obra —el resultado común que ha de evitarse—. 28

### **French Transformations**

#### **Double Punctuation Spacing Normalization**

* **Before (Legacy/Aesthetic French Space):**  
  Il déclara : « Est-ce que tout le monde est prêt? » ; personne ne répondit.  
* **After (Unified AI-Ready "English Tight"):** Il déclara: «Est-ce que tout le monde est prêt?»; personne ne répondit.31

#### **French Elision and Quote Hierarchy**

* **Before (Legacy/Aesthetic):**  
  Il dit: "C'est l'homme qui a crié 'Victoire\!'".  
* **After (Unified AI-Ready):** Il dit: «C’est l’homme qui a crié “Victoire\!”».24

## **Actionable Architectural Recommendations**

To implement this standard successfully within the Books2MD converter pipeline, the following engineering steps are recommended:

1. **Tokenizer Boundary Optimization:** The conversion pipeline must automatically replace all unspaced em-dashes used for parenthetical thoughts with spaced en-dashes (–) in the Markdown output.10 This prevents the merging of punctuation and text into rare, high-cost tokens.3  
2. **Canonical Quotation Hierarchy Enforcement:** All quotation marks must be mapped to the standardized hierarchy (« » ![][image1] “ ” ![][image1] ‘ ’) during preprocessing, regardless of the source document's original language.31 This simplifies translation databases and regular expression rules in RAG systems.24  
3. **Strict Logical Punctuation Migration:** Commas and periods must be shifted outside quotation boundaries unless they are part of the literal source text being quoted.33 This preserves the use/mention distinction, ensuring clean data indexing and retrieval.32  
4. **Whitespace Normalization:** The pipeline must strip all multi-byte Unicode spaces—such as narrow no-break spaces (U+202F) and thin spaces (U+2009)—and replace them with standard ASCII spaces (U+0020).39 Punctuation must be set "tight" to the preceding word, relying on downstream rendering templates (like Pandoc's smart punctuation extension) to handle local spacing styles for human-facing outputs.39  
5. **Validation Testing:** The converter must include automated unit tests to verify that range dashes remain unspaced, that date patterns follow ISO 8601 formatting, and that parenthetical dashes are correctly swallowed in English but preserved in Spanish and French.18

#### **Obras citadas**

1. A Comprehensive Analysis of Tokenization and Self-Supervised Learning in End-to-End Automatic Speech Recognition applied on French Language \- arXiv, fecha de acceso: junio 7, 2026, [https://arxiv.org/html/2605.03696v1](https://arxiv.org/html/2605.03696v1)  
2. Tokenization and Embeddings: How Generative AI Understands Language, fecha de acceso: junio 7, 2026, [https://www.ascendientlearning.com/blog/how-genai-understands-language](https://www.ascendientlearning.com/blog/how-genai-understands-language)  
3. How Tokenization & Embedding Actually Work | by Aman Shekhar \- Medium, fecha de acceso: junio 7, 2026, [https://shekhar14.medium.com/how-tokenization-embedding-actually-work-56f3acd6f3fd](https://shekhar14.medium.com/how-tokenization-embedding-actually-work-56f3acd6f3fd)  
4. Incorrect tokenization of dash punctuation in Spanish when not preceded or followed by a space · explosion spaCy · Discussion \#13055 \- GitHub, fecha de acceso: junio 7, 2026, [https://github.com/explosion/spaCy/discussions/13055](https://github.com/explosion/spaCy/discussions/13055)  
5. Chapter 4 — Tokens across languages \- Zenn, fecha de acceso: junio 7, 2026, [https://zenn.dev/shinyay/books/getting-started-with-tokens-en/viewer/05-tokens-across-languages](https://zenn.dev/shinyay/books/getting-started-with-tokens-en/viewer/05-tokens-across-languages)  
6. The Last Fingerprint: How Markdown Training Shapes LLM Prose \- arXiv, fecha de acceso: junio 7, 2026, [https://arxiv.org/html/2603.27006v1](https://arxiv.org/html/2603.27006v1)  
7. How did the em dash become the signature AI detection punctuation? : r/ChatGPT \- Reddit, fecha de acceso: junio 7, 2026, [https://www.reddit.com/r/ChatGPT/comments/1jhmyd9/how\_did\_the\_em\_dash\_become\_the\_signature\_ai/](https://www.reddit.com/r/ChatGPT/comments/1jhmyd9/how_did_the_em_dash_become_the_signature_ai/)  
8. Why do AI models keep outputting em dashes (—) instead of hyphens (-)? \- Reddit, fecha de acceso: junio 7, 2026, [https://www.reddit.com/r/LanguageTechnology/comments/1mq2p8i/why\_do\_ai\_models\_keep\_outputting\_em\_dashes/](https://www.reddit.com/r/LanguageTechnology/comments/1mq2p8i/why_do_ai_models_keep_outputting_em_dashes/)  
9. Why do AI models use so many em-dashes? \- Sean Goedecke, fecha de acceso: junio 7, 2026, [https://www.seangoedecke.com/em-dashes/](https://www.seangoedecke.com/em-dashes/)  
10. How do you all feel about the em dash? Is it still the hallmark of AI generated content, or have we moved past that? \- Reddit, fecha de acceso: junio 7, 2026, [https://www.reddit.com/r/Design/comments/1rcre4s/how\_do\_you\_all\_feel\_about\_the\_em\_dash\_is\_it\_still/](https://www.reddit.com/r/Design/comments/1rcre4s/how_do_you_all_feel_about_the_em_dash_is_it_still/)  
11. Should you have a space around an em dash? \- Quora, fecha de acceso: junio 7, 2026, [https://www.quora.com/Should-you-have-a-space-around-an-em-dash](https://www.quora.com/Should-you-have-a-space-around-an-em-dash)  
12. Should I put a space after an em dash that 'clips off' part of dialogue ('What-- What are you-- ' as opposed to 'What--What are you--') in Chicago style? \- Quora, fecha de acceso: junio 7, 2026, [https://www.quora.com/Should-I-put-a-space-after-an-em-dash-that-clips-off-part-of-dialogue-What-What-are-you-as-opposed-to-What-What-are-you-in-Chicago-style-1](https://www.quora.com/Should-I-put-a-space-after-an-em-dash-that-clips-off-part-of-dialogue-What-What-are-you-as-opposed-to-What-What-are-you-in-Chicago-style-1)  
13. punctuation \- Dashes: \- vs. – vs. — \- TeX \- LaTeX Stack Exchange, fecha de acceso: junio 7, 2026, [https://tex.stackexchange.com/questions/3819/dashes-vs-vs](https://tex.stackexchange.com/questions/3819/dashes-vs-vs)  
14. Violation of DIN 5008? : r/DINgore \- Reddit, fecha de acceso: junio 7, 2026, [https://www.reddit.com/r/DINgore/comments/1n78pgc/versto%C3%9F\_gegen\_din\_5008/?tl=en](https://www.reddit.com/r/DINgore/comments/1n78pgc/versto%C3%9F_gegen_din_5008/?tl=en)  
15. Cover letter header: Address, City, Date & Subject \- Tutkit.com, fecha de acceso: junio 7, 2026, [https://www.tutkit.com/en/application-resume-cv/236-cover-letter-header-address-city-date-und-subject](https://www.tutkit.com/en/application-resume-cv/236-cover-letter-header-address-city-date-und-subject)  
16. Das bis-Zeichen und seine Länge \- Fragen Sie Dr. Bopp\!, fecha de acceso: junio 7, 2026, [https://blog.leo.org/2020/10/23/das-bis-zeichen-und-seine-laenge/](https://blog.leo.org/2020/10/23/das-bis-zeichen-und-seine-laenge/)  
17. Die Verwendung des Mittestrichs nach DIN 5008 \- Lehrerfortbildung-bw.de, fecha de acceso: junio 7, 2026, [https://lehrerfortbildung-bw.de/s\_bs/berufsbezogen/wirtschaft/bueromanagement/fb1/text/tast/mittestrich/](https://lehrerfortbildung-bw.de/s_bs/berufsbezogen/wirtschaft/bueromanagement/fb1/text/tast/mittestrich/)  
18. En dash \- The Punctuation Guide, fecha de acceso: junio 7, 2026, [https://www.thepunctuationguide.com/en-dash.html](https://www.thepunctuationguide.com/en-dash.html)  
19. Dashes | Style Manual, fecha de acceso: junio 7, 2026, [https://www.stylemanual.gov.au/grammar-punctuation-and-conventions/punctuation/dashes](https://www.stylemanual.gov.au/grammar-punctuation-and-conventions/punctuation/dashes)  
20. Hyphens, En Dashes, and Em Dashes: Differences, Similarities, and Uses \- San Jose State University, fecha de acceso: junio 7, 2026, [https://www.sjsu.edu/writingcenter/docs/handouts/Hyphens%20Dashes.pdf](https://www.sjsu.edu/writingcenter/docs/handouts/Hyphens%20Dashes.pdf)  
21. Hyphen \- Wikipedia, fecha de acceso: junio 7, 2026, [https://en.wikipedia.org/wiki/Hyphen](https://en.wikipedia.org/wiki/Hyphen)  
22. Hyphens, En‐Dashes and Em‐Dashes, fecha de acceso: junio 7, 2026, [https://www.iavceivolcano.org/content/uploads/2023/05/bulletin-of-volcanology-hyphens-and-em-en-dashes.pdf](https://www.iavceivolcano.org/content/uploads/2023/05/bulletin-of-volcanology-hyphens-and-em-en-dashes.pdf)  
23. ISO 8601 \- Wikipedia, fecha de acceso: junio 7, 2026, [https://en.wikipedia.org/wiki/ISO\_8601](https://en.wikipedia.org/wiki/ISO_8601)  
24. Tokenization \- Stanford NLP Group, fecha de acceso: junio 7, 2026, [https://nlp.stanford.edu/IR-book/html/htmledition/tokenization-1.html](https://nlp.stanford.edu/IR-book/html/htmledition/tokenization-1.html)  
25. Punctuation \- APSA Connect, fecha de acceso: junio 7, 2026, [https://connect.apsanet.org/stylemanual/sample-page/punctuation/](https://connect.apsanet.org/stylemanual/sample-page/punctuation/)  
26. CMOS Site Search Page \- The Chicago Manual of Style, fecha de acceso: junio 7, 2026, [https://www.chicagomanualofstyle.org/search.html?clause=em+dash](https://www.chicagomanualofstyle.org/search.html?clause=em+dash)  
27. The Hyphen and the Dash \- University of Sussex, fecha de acceso: junio 7, 2026, [https://www.sussex.ac.uk/informatics/punctuation/hyphenanddash/dash](https://www.sussex.ac.uk/informatics/punctuation/hyphenanddash/dash)  
28. FAOSTYLE-\>Puntuación \- FAO Knowledge Repository, fecha de acceso: junio 7, 2026, [https://openknowledge.fao.org/server/api/core/bitstreams/6a193e80-a467-43ee-9370-9df3df0fd8db/content/punctuation-es.html](https://openknowledge.fao.org/server/api/core/bitstreams/6a193e80-a467-43ee-9370-9df3df0fd8db/content/punctuation-es.html)  
29. Cómo puntuar diálogos correctamente \- Café del Escritor, fecha de acceso: junio 7, 2026, [https://www.cafedelescritor.com/como-puntuar-dialogos-correctamente/](https://www.cafedelescritor.com/como-puntuar-dialogos-correctamente/)  
30. Hyphens, En Dashes, Em Dashes \- The Chicago Manual of Style, fecha de acceso: junio 7, 2026, [https://www.chicagomanualofstyle.org/qanda/data/faq/topics/HyphensEnDashesEmDashes/faq0175.html](https://www.chicagomanualofstyle.org/qanda/data/faq/topics/HyphensEnDashesEmDashes/faq0175.html)  
31. Signos de Puntuación según la RAE | PDF \- Scribd, fecha de acceso: junio 7, 2026, [https://es.scribd.com/document/804739154/TEMA-3-LA-PUNTUACION](https://es.scribd.com/document/804739154/TEMA-3-LA-PUNTUACION)  
32. Logical Punctuation Isn't the Logical Choice \- DAILY WRITING TIPS, fecha de acceso: junio 7, 2026, [https://www.dailywritingtips.com/logical-punctuation-isn%E2%80%99t-the-logical-choice/](https://www.dailywritingtips.com/logical-punctuation-isn%E2%80%99t-the-logical-choice/)  
33. Wikipedia talk:Manual of Style/quotation and punctuation, fecha de acceso: junio 7, 2026, [https://en.wikipedia.org/wiki/Wikipedia\_talk:Manual\_of\_Style/quotation\_and\_punctuation](https://en.wikipedia.org/wiki/Wikipedia_talk:Manual_of_Style/quotation_and_punctuation)  
34. Punctuation & Quotation Conventions \- LessWrong, fecha de acceso: junio 7, 2026, [https://www.lesswrong.com/posts/YgedrNsdXNajQ7oCT/punctuation-and-quotation-conventions](https://www.lesswrong.com/posts/YgedrNsdXNajQ7oCT/punctuation-and-quotation-conventions)  
35. CORE Econ Publishing Documentation The CORE editorial house style, fecha de acceso: junio 7, 2026, [https://books.core-econ.org/docs/book/01-01-core-editorial-house-style.html](https://books.core-econ.org/docs/book/01-01-core-editorial-house-style.html)  
36. Content Editing \- Visual R Markdown \- rstudio.github.io, fecha de acceso: junio 7, 2026, [https://rstudio.github.io/visual-markdown-editing/content.html](https://rstudio.github.io/visual-markdown-editing/content.html)  
37. Proceedings of the 12th Workshop on Challenges in the Management of Large Corpora (CMLC-12) \- LREC, fecha de acceso: junio 7, 2026, [http://lrec-conf.org/proceedings/lrec2026/workshops/cmlc/2026.cmlc-1.0.pdf](http://lrec-conf.org/proceedings/lrec2026/workshops/cmlc/2026.cmlc-1.0.pdf)  
38. Releases \- Pandoc, fecha de acceso: junio 7, 2026, [https://pandoc.org/releases.html](https://pandoc.org/releases.html)  
39. GPT-5 (non-reasoning) outputs U+202F (narrow no-break space) instead of normal spaces — breaks text rendering on macOS apps \- OpenAI Developer Community, fecha de acceso: junio 7, 2026, [https://community.openai.com/t/gpt-5-non-reasoning-outputs-u-202f-narrow-no-break-space-instead-of-normal-spaces-breaks-text-rendering-on-macos-apps/1362321](https://community.openai.com/t/gpt-5-non-reasoning-outputs-u-202f-narrow-no-break-space-instead-of-normal-spaces-breaks-text-rendering-on-macos-apps/1362321)  
40. Detecting cyberbullying text using the approaches with machine learning models for the low-resource Bengali language \- ResearchGate, fecha de acceso: junio 7, 2026, [https://www.researchgate.net/publication/376757358\_Detecting\_cyberbullying\_text\_using\_the\_approaches\_with\_machine\_learning\_models\_for\_the\_low-resource\_Bengali\_language](https://www.researchgate.net/publication/376757358_Detecting_cyberbullying_text_using_the_approaches_with_machine_learning_models_for_the_low-resource_Bengali_language)  
41. Detecting cyberbullying text using the approaches with machine learning models for the low-resource Bengali language \- Semantic Scholar, fecha de acceso: junio 7, 2026, [https://pdfs.semanticscholar.org/b75d/34c1965347046b4768ab70ae20bf595c0720.pdf](https://pdfs.semanticscholar.org/b75d/34c1965347046b4768ab70ae20bf595c0720.pdf)  
42. an on-device AI application for real-time science-based consumer education on food additives using retrieval-augmented generation \- RSC Publishing, fecha de acceso: junio 7, 2026, [https://pubs.rsc.org/en/content/articlehtml/2026/dd/d5dd00444f](https://pubs.rsc.org/en/content/articlehtml/2026/dd/d5dd00444f)  
43. Leitfaden \- Typografische Gestaltung einer wissenschaftlichen Arbeit, fecha de acceso: junio 7, 2026, [https://mv.hs-duesseldorf.de/personen/carl-justus-heckmann/Documents/Leitfaden%20-%20Wissenschaftliche%20Arbeit%20(Version%201.3).pdf](https://mv.hs-duesseldorf.de/personen/carl-justus-heckmann/Documents/Leitfaden%20-%20Wissenschaftliche%20Arbeit%20\(Version%201.3\).pdf)  
44. Pandoc User's Guide \- Smart punctuation \- Universitat de València, fecha de acceso: junio 7, 2026, [https://www.uv.es/wiki/pandoc\_manual\_instalado.wiki?37](https://www.uv.es/wiki/pandoc_manual_instalado.wiki?37)  
45. Content Editing \- Quarto, fecha de acceso: junio 7, 2026, [https://quarto.org/docs/visual-editor/content.html](https://quarto.org/docs/visual-editor/content.html)  
46. Processings of the 1st Workshop on NLP for Languages Using Arabic Script (AbjadNLP) \- ACL Anthology, fecha de acceso: junio 7, 2026, [https://aclanthology.org/2025.abjadnlp-1.pdf](https://aclanthology.org/2025.abjadnlp-1.pdf)  
47. Can anyone help me develop a rationale for putting end-sentence punctuation inside of quotation marks? : r/grammar \- Reddit, fecha de acceso: junio 7, 2026, [https://www.reddit.com/r/grammar/comments/1nkdyd5/can\_anyone\_help\_me\_develop\_a\_rationale\_for/](https://www.reddit.com/r/grammar/comments/1nkdyd5/can_anyone_help_me_develop_a_rationale_for/)  
48. Topic Q\&A List \- The Chicago Manual of Style, fecha de acceso: junio 7, 2026, [https://www.chicagomanualofstyle.org/qanda/data/faq/topics/Punctuation.html?page=3](https://www.chicagomanualofstyle.org/qanda/data/faq/topics/Punctuation.html?page=3)  
49. Journal of Music Theory Pedagogy: Final Manuscript Preparation Guidelines, fecha de acceso: junio 7, 2026, [https://digitalcollections.lipscomb.edu/jmtp/styleguide.html](https://digitalcollections.lipscomb.edu/jmtp/styleguide.html)  
50. Ortotipografía de la raya en oraciones parentéticas \- Nisaba \- WordPress.com, fecha de acceso: junio 7, 2026, [https://blognisaba.wordpress.com/2010/03/20/ortotipografia-de-la-raya-en-oraciones-parenteticas/](https://blognisaba.wordpress.com/2010/03/20/ortotipografia-de-la-raya-en-oraciones-parenteticas/)  
51. La ortografía académica del 2010: cara y dorso | La Linterna del ..., fecha de acceso: junio 7, 2026, [https://lalinternadeltraductor.org/n5/ortografia-2010.html](https://lalinternadeltraductor.org/n5/ortografia-2010.html)  
52. Date and time notation in the United States \- Wikipedia, fecha de acceso: junio 7, 2026, [https://en.wikipedia.org/wiki/Date\_and\_time\_notation\_in\_the\_United\_States](https://en.wikipedia.org/wiki/Date_and_time_notation_in_the_United_States)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAZCAYAAADe1WXtAAAAcElEQVR4XmNgGAWjYFCAdiCWRBekFEwG4mR0QUqBFRBfQBekBpAF4lx0QWqAO0C8EYh10SVAIBWId5OB7wHxfyBeDcTMDFQCIEMt0QUpASDDsHqbXGALxFvQBSkFM4A4AF2QUgBK+PzogqNgFNAIAADWvRUcqAhrOQAAAABJRU5ErkJggg==>