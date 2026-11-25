"""
Moteur de syntaxe booléenne scientifique standardisée (PRISMA / PubMed Entrez / OpenAlex / Semantic Scholar).

Supporte :
- Opérateurs booléens : AND (ET, &), OR (OU, |), NOT (SAUF, -, !) avec priorité NOT > AND > OR et AND implicite
- Groupements parenthétiques imbriqués (...)
- Expressions exactes entre guillemets "..."
- Troncature préfixe : terme* (ex: endur*, thermoregul*)
- Qualificateurs de champs en préfixe (ti:, title:, ab:, abstract:, tiab:, au:, author:, jo:, journal:, mesh:, mh:, doi:, pmid:, tag:)
  et en suffixe PubMed entre crochets ([Title], [Abstract], [Title/Abstract], [TIAB], [Author], [AU], [Journal], [TA], [MeSH Terms], [MeSH], [MH])
- Compilateurs vers les API PubMed, OpenAlex, Semantic Scholar (/paper/search/bulk & /paper/search) et Crossref
- Évaluateur en mémoire sur RawPublication, ClassifiedPublication ou dict
"""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Optional, Tuple, Union


FIELD_ALIASES: Dict[str, str] = {
    "all": "all",
    "any": "all",
    "ti": "ti",
    "title": "ti",
    "ab": "ab",
    "abstract": "ab",
    "tiab": "tiab",
    "title/abstract": "tiab",
    "title_abstract": "tiab",
    "au": "au",
    "author": "au",
    "authors": "au",
    "fau": "au",
    "jo": "jo",
    "journal": "jo",
    "ta": "jo",
    "so": "jo",
    "mesh": "mesh",
    "mh": "mesh",
    "mesh terms": "mesh",
    "mesh_terms": "mesh",
    "doi": "doi",
    "lid": "doi",
    "aid": "doi",
    "pmid": "pmid",
    "tag": "tag",
    "tags": "tag",
    "kw": "tag",
    "ot": "tag",
}

PUBMED_FIELD_TAGS: Dict[str, str] = {
    "all": "",
    "ti": "[Title]",
    "ab": "[Title/Abstract]",
    "tiab": "[Title/Abstract]",
    "au": "[Author]",
    "jo": "[Journal]",
    "mesh": "[MeSH Terms]",
    "doi": "[Location ID]",
    "pmid": "[PMID]",
    "tag": "[Other Term]",
}

PUBMED_PUBLICATION_TYPES: Dict[str, str] = {
    "meta_analysis": '"Meta-Analysis"[Publication Type]',
    "systematic_review": '"Systematic Review"[Publication Type]',
    "randomized_controlled_trial": '"Randomized Controlled Trial"[Publication Type]',
    "controlled_trial": '("Clinical Trial"[Publication Type] OR "Controlled Clinical Trial"[Publication Type])',
    "consensus_statement": '("Consensus Development Conference"[Publication Type] OR "Practice Guideline"[Publication Type] OR "Guideline"[Publication Type])',
    "cohort_study": '"Cohort Studies"[MeSH Terms]',
    "observational_study": '"Observational Study"[Publication Type]',
    "narrative_review": '"Review"[Publication Type]',
    "case_study": '"Case Reports"[Publication Type]',
}

S2_PUBLICATION_TYPES: Dict[str, str] = {
    "meta_analysis": "MetaAnalysis",
    "systematic_review": "Review",
    "randomized_controlled_trial": "ClinicalTrial",
    "controlled_trial": "ClinicalTrial",
    "consensus_statement": "Review",
    "cohort_study": "Study",
    "observational_study": "Study",
    "narrative_review": "Review",
    "case_study": "CaseReport",
}

LANGUAGE_PUBMED_MAP: Dict[str, str] = {
    "en": '"english"[Language]',
    "fr": '"french"[Language]',
    "es": '"spanish"[Language]',
    "de": '"german"[Language]',
    "it": '"italian"[Language]',
    "pt": '"portuguese"[Language]',
}

# Taxonomie officielle PEDro (search.pedro.org.au/advanced-search)
PEDRO_SUBDISCIPLINES: Dict[str, Dict[str, str]] = {
    "sports": {
        "code": "VL01361",
        "label": "Sports",
        "pubmed": '("Sports Medicine"[MeSH Terms] OR "Athletic Injuries"[MeSH Terms] OR sport*[Title/Abstract] OR athlete*[Title/Abstract])',
    },
    "musculoskeletal": {
        "code": "VL01356",
        "label": "Musculo-squelettique",
        "pubmed": '("Musculoskeletal Diseases"[MeSH Terms] OR musculoskeletal[Title/Abstract] OR tendon[Title/Abstract] OR ligament[Title/Abstract])',
    },
    "orthopaedics": {
        "code": "VL01359",
        "label": "Orthopédie",
        "pubmed": '("Orthopedics"[MeSH Terms] OR orthopedic*[Title/Abstract] OR orthopaedic*[Title/Abstract])',
    },
    "cardiothoracics": {
        "code": "VL01352",
        "label": "Cardio-respiratoire",
        "pubmed": '("Cardiopulmonary"[Title/Abstract] OR respiratory[Title/Abstract] OR "cardiac rehabilitation"[Title/Abstract])',
    },
    "neurology": {
        "code": "VL01357",
        "label": "Neurologie",
        "pubmed": '("Neurology"[MeSH Terms] OR neurological[Title/Abstract] OR neuromuscular[Title/Abstract])',
    },
    "gerontology": {
        "code": "VL01355",
        "label": "Gérontologie",
        "pubmed": '("Aged"[MeSH Terms] OR "older adult*"[Title/Abstract] OR geriatric*[Title/Abstract])',
    },
    "paediatrics": {
        "code": "VL01360",
        "label": "Pédiatrie",
        "pubmed": '("Pediatrics"[MeSH Terms] OR pediatric*[Title/Abstract] OR youth[Title/Abstract] OR adolescent*[Title/Abstract])',
    },
    "ergonomics": {
        "code": "VL01354",
        "label": "Ergonomie & Santé au travail",
        "pubmed": '("Ergonomics"[MeSH Terms] OR occupational[Title/Abstract])',
    },
    "continence": {
        "code": "VL01353",
        "label": "Santé féminine / Pelvienne",
        "pubmed": '("Women"[MeSH Terms] OR "pelvic floor"[Title/Abstract] OR incontinence[Title/Abstract])',
    },
}

PEDRO_THERAPIES: Dict[str, Dict[str, str]] = {
    "strength_training": {
        "code": "VL01387",
        "label": "Renforcement musculaire",
        "pubmed": '("Resistance Training"[MeSH Terms] OR "strength training"[Title/Abstract] OR eccentric[Title/Abstract] OR isometric[Title/Abstract])',
    },
    "fitness_training": {
        "code": "VL01380",
        "label": "Entraînement physique / Fitness",
        "pubmed": '("Exercise Therapy"[MeSH Terms] OR "aerobic training"[Title/Abstract] OR endurance[Title/Abstract] OR conditioning[Title/Abstract])',
    },
    "stretching_mobilisation_massage": {
        "code": "VL01388",
        "label": "Étirements, mobilisation & massage",
        "pubmed": '("Musculoskeletal Manipulations"[MeSH Terms] OR stretching[Title/Abstract] OR mobilisation[Title/Abstract] OR mobilization[Title/Abstract] OR massage[Title/Abstract])',
    },
    "orthoses_taping_splinting": {
        "code": "VL01384",
        "label": "Orthèses, taping & contention",
        "pubmed": '("Orthotic Devices"[MeSH Terms] OR orthos*[Title/Abstract] OR taping[Title/Abstract] OR insole*[Title/Abstract] OR compression[Title/Abstract])',
    },
    "electrotherapies_heat_cold": {
        "code": "VL01379",
        "label": "Électrothérapie, chaud & cryothérapie",
        "pubmed": '("Cryotherapy"[MeSH Terms] OR "Electric Stimulation Therapy"[MeSH Terms] OR cryotherapy[Title/Abstract] OR cold[Title/Abstract] OR heat[Title/Abstract] OR ultrasound[Title/Abstract])',
    },
    "skill_training": {
        "code": "VL01386",
        "label": "Entraînement moteur & technique",
        "pubmed": '(propriocept*[Title/Abstract] OR balance[Title/Abstract] OR gait[Title/Abstract] OR neuromuscular[Title/Abstract])',
    },
    "education": {
        "code": "VL01378",
        "label": "Éducation & prévention patient",
        "pubmed": '("Patient Education as Topic"[MeSH Terms] OR education[Title/Abstract] OR advice[Title/Abstract])',
    },
}


@dataclass(frozen=True)
class TermNode:
    value: str
    quoted: bool = False
    wildcard: bool = False
    field: str = "all"


@dataclass(frozen=True)
class NotNode:
    child: "BooleanAstNode"


@dataclass(frozen=True)
class AndNode:
    left: "BooleanAstNode"
    right: "BooleanAstNode"


@dataclass(frozen=True)
class OrNode:
    left: "BooleanAstNode"
    right: "BooleanAstNode"


BooleanAstNode = Union[TermNode, NotNode, AndNode, OrNode]


class BooleanSyntaxError(ValueError):
    """Erreur de syntaxe dans une équation booléenne."""


@dataclass
class _Token:
    kind: str  # LPAREN, RPAREN, AND, OR, NOT, TERM, BRACKET_FIELD
    value: str = ""
    quoted: bool = False
    wildcard: bool = False
    field: str = "all"


def normalize_field_name(raw_field: str) -> Optional[str]:
    cleaned = raw_field.strip().lower().strip("[]").strip()
    return FIELD_ALIASES.get(cleaned)


def _tokenize_boolean_query(raw: str) -> List[_Token]:
    tokens: List[_Token] = []
    text = (raw or "").strip()
    n = len(text)
    i = 0

    while i < n:
        ch = text[i]
        if ch.isspace() or ch in ",;":
            i += 1
            continue

        if ch == "(":
            tokens.append(_Token(kind="LPAREN", value="("))
            i += 1
            continue

        if ch == ")":
            tokens.append(_Token(kind="RPAREN", value=")"))
            i += 1
            continue

        if ch in ("&", "|"):
            op = "AND" if ch == "&" else "OR"
            if i + 1 < n and text[i + 1] == ch:
                i += 2
            else:
                i += 1
            tokens.append(_Token(kind=op, value=op))
            continue

        if ch == "!":
            tokens.append(_Token(kind="NOT", value="NOT"))
            i += 1
            continue

        if ch == "[":
            end_br = text.find("]", i + 1)
            if end_br == -1:
                raise BooleanSyntaxError("Crochet '[' non fermé dans la requête.")
            field_raw = text[i + 1 : end_br]
            norm_field = normalize_field_name(field_raw)
            if norm_field:
                tokens.append(_Token(kind="BRACKET_FIELD", field=norm_field, value=field_raw))
            i = end_br + 1
            continue

        # Préfixe '-' avant un terme ou une parenthèse (ex: -rat, -(mice OR rat))
        if ch == "-" and (i + 1 < n) and not text[i + 1].isspace():
            tokens.append(_Token(kind="NOT", value="NOT"))
            i += 1
            continue

        # Préfixe champ:valeur ou champ:"phrase"
        prefix_field = "all"
        if ch != '"':
            colon_match = re.match(r"([A-Za-z_]{2,16}):", text[i:])
            if colon_match:
                cand_field = normalize_field_name(colon_match.group(1))
                if cand_field is not None:
                    prefix_field = cand_field
                    i += colon_match.end()
                    if i >= n:
                        raise BooleanSyntaxError(f"Terme manquant après '{colon_match.group(0)}'.")

        if i < n and text[i] == '"':
            i += 1
            start_q = i
            while i < n and text[i] != '"':
                i += 1
            if i >= n:
                raise BooleanSyntaxError('Guillemet ouvrant (") non fermé dans la requête.')
            phrase = text[start_q:i].strip()
            i += 1
            if not phrase:
                raise BooleanSyntaxError("Expression exacte vide entre guillemets.")
            wildcard = False
            if phrase.endswith("*") and len(phrase) > 2:
                wildcard = True
                phrase = phrase[:-1].strip()
            if i < n and text[i] == "*":
                wildcard = True
                i += 1
            field = prefix_field
            if i < n and text[i] == "[":
                end_br = text.find("]", i + 1)
                if end_br == -1:
                    raise BooleanSyntaxError("Crochet '[' non fermé après l'expression.")
                norm_field = normalize_field_name(text[i + 1 : end_br])
                if norm_field:
                    field = norm_field
                i = end_br + 1
            tokens.append(_Token(kind="TERM", value=phrase, quoted=True, wildcard=wildcard, field=field))
            continue

        # Mot simple jusqu'au prochain délimiteur
        start_w = i
        while i < n and not text[i].isspace() and text[i] not in '()[],"&|!':
            i += 1
        word = text[start_w:i].strip()
        if not word:
            continue

        upper_word = word.upper()
        if prefix_field == "all":
            if upper_word in ("AND", "ET"):
                tokens.append(_Token(kind="AND", value="AND"))
                continue
            if upper_word in ("OR", "OU"):
                tokens.append(_Token(kind="OR", value="OR"))
                continue
            if upper_word in ("NOT", "SAUF"):
                tokens.append(_Token(kind="NOT", value="NOT"))
                continue

        wildcard = False
        if word.endswith("*") and len(word) >= 2:
            wildcard = True
            word = word[:-1]

        field = prefix_field
        if i < n and text[i] == "[":
            end_br = text.find("]", i + 1)
            if end_br == -1:
                raise BooleanSyntaxError("Crochet '[' non fermé après le terme.")
            norm_field = normalize_field_name(text[i + 1 : end_br])
            if norm_field:
                field = norm_field
            i = end_br + 1

        tokens.append(_Token(kind="TERM", value=word, quoted=False, wildcard=wildcard, field=field))

    return tokens


def _apply_field_to_ast(node: BooleanAstNode, field: str) -> BooleanAstNode:
    if field == "all":
        return node
    if isinstance(node, TermNode):
        return replace(node, field=field if node.field == "all" else node.field)
    if isinstance(node, NotNode):
        return NotNode(child=_apply_field_to_ast(node.child, field))
    if isinstance(node, AndNode):
        return AndNode(
            left=_apply_field_to_ast(node.left, field),
            right=_apply_field_to_ast(node.right, field),
        )
    if isinstance(node, OrNode):
        return OrNode(
            left=_apply_field_to_ast(node.left, field),
            right=_apply_field_to_ast(node.right, field),
        )
    return node


class _BooleanParser:
    def __init__(self, tokens: List[_Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Optional[_Token]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _consume(self) -> _Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def parse(self) -> Optional[BooleanAstNode]:
        if not self.tokens:
            return None
        node = self._parse_or()
        if self.pos < len(self.tokens):
            tok = self.tokens[self.pos]
            if tok.kind == "RPAREN":
                raise BooleanSyntaxError("Parenthèse fermante ')' sans parenthèse ouvrante correspondante.")
            raise BooleanSyntaxError(f"Jeton inattendu '{tok.value}' dans la requête.")
        return node

    def _parse_or(self) -> BooleanAstNode:
        left = self._parse_and()
        while (tok := self._peek()) is not None and tok.kind == "OR":
            self._consume()
            right = self._parse_and()
            left = OrNode(left=left, right=right)
        return left

    def _parse_and(self) -> BooleanAstNode:
        left = self._parse_not()
        while (tok := self._peek()) is not None:
            if tok.kind == "AND":
                self._consume()
                right = self._parse_not()
                left = AndNode(left=left, right=right)
            elif tok.kind in ("TERM", "LPAREN", "NOT"):
                # AND implicite entre deux expressions adjacentes
                right = self._parse_not()
                left = AndNode(left=left, right=right)
            else:
                break
        return left

    def _parse_not(self) -> BooleanAstNode:
        tok = self._peek()
        if tok is not None and tok.kind == "NOT":
            self._consume()
            child = self._parse_not()
            return NotNode(child=child)
        return self._parse_primary()

    def _parse_primary(self) -> BooleanAstNode:
        tok = self._peek()
        if tok is None:
            raise BooleanSyntaxError("Fin de requête inattendue après un opérateur.")
        if tok.kind == "LPAREN":
            self._consume()
            if (nxt := self._peek()) is not None and nxt.kind == "RPAREN":
                raise BooleanSyntaxError("Groupe de parenthèses vide '()'.")
            inner = self._parse_or()
            closing = self._peek()
            if closing is None or closing.kind != "RPAREN":
                raise BooleanSyntaxError("Parenthèse ouvrante '(' non fermée.")
            self._consume()
            if (br := self._peek()) is not None and br.kind == "BRACKET_FIELD":
                self._consume()
                inner = _apply_field_to_ast(inner, br.field)
            return inner
        if tok.kind == "TERM":
            self._consume()
            return TermNode(
                value=tok.value,
                quoted=tok.quoted,
                wildcard=tok.wildcard,
                field=tok.field,
            )
        if tok.kind in ("AND", "OR"):
            raise BooleanSyntaxError(f"Opérateur '{tok.value}' mal placé sans opérande gauche.")
        if tok.kind == "RPAREN":
            raise BooleanSyntaxError("Parenthèse fermante ')' inattendue.")
        raise BooleanSyntaxError(f"Jeton inattendu '{tok.value}'.")


def parse_boolean_query(query: str) -> Optional[BooleanAstNode]:
    """Parse une équation booléenne scientifique en AST. Lève BooleanSyntaxError si invalide."""
    tokens = _tokenize_boolean_query(query)
    if not tokens:
        return None
    return _BooleanParser(tokens).parse()


def _format_term_canonical(node: TermNode) -> str:
    core = f'"{node.value}"' if (node.quoted or " " in node.value) else node.value
    if node.wildcard:
        core = f"{core}*"
    if node.field != "all":
        return f"{node.field}:{core}"
    return core


def format_ast_canonical(node: BooleanAstNode, parent_op: str = "") -> str:
    """Reformate proprement un AST booléen sous forme canonique."""
    if isinstance(node, TermNode):
        return _format_term_canonical(node)
    if isinstance(node, NotNode):
        inner = format_ast_canonical(node.child, "NOT")
        if isinstance(node.child, (AndNode, OrNode)):
            return f"NOT ({inner})"
        return f"NOT {inner}"
    if isinstance(node, AndNode):
        txt = f"{format_ast_canonical(node.left, 'AND')} AND {format_ast_canonical(node.right, 'AND')}"
        return f"({txt})" if parent_op in ("NOT",) else txt
    if isinstance(node, OrNode):
        txt = f"{format_ast_canonical(node.left, 'OR')} OR {format_ast_canonical(node.right, 'OR')}"
        return f"({txt})" if parent_op in ("AND", "NOT") else txt
    return ""


def _collect_terms(
    node: Optional[BooleanAstNode],
    negated: bool = False,
    pos: Optional[List[TermNode]] = None,
    neg: Optional[List[TermNode]] = None,
) -> Tuple[List[TermNode], List[TermNode]]:
    pos_list = pos if pos is not None else []
    neg_list = neg if neg is not None else []
    if node is None:
        return pos_list, neg_list
    if isinstance(node, TermNode):
        (neg_list if negated else pos_list).append(node)
    elif isinstance(node, NotNode):
        _collect_terms(node.child, not negated, pos_list, neg_list)
    elif isinstance(node, (AndNode, OrNode)):
        _collect_terms(node.left, negated, pos_list, neg_list)
        _collect_terms(node.right, negated, pos_list, neg_list)
    return pos_list, neg_list


def validate_boolean_query(query: str) -> Dict[str, Any]:
    """Valide une requête booléenne et retourne son équation normalisée + termes positifs/négatifs."""
    raw = (query or "").strip()
    if not raw:
        return {
            "valid": True,
            "error": None,
            "normalized": "",
            "positive_terms": [],
            "negative_terms": [],
        }
    try:
        ast = parse_boolean_query(raw)
        pos_nodes, neg_nodes = _collect_terms(ast)
        pos_terms = list(dict.fromkeys(t.value.lower() for t in pos_nodes if t.value.strip()))
        neg_terms = list(dict.fromkeys(t.value.lower() for t in neg_nodes if t.value.strip()))
        normalized = format_ast_canonical(ast) if ast else ""
        return {
            "valid": True,
            "error": None,
            "normalized": normalized,
            "positive_terms": pos_terms,
            "negative_terms": neg_terms,
        }
    except BooleanSyntaxError as err:
        return {
            "valid": False,
            "error": str(err),
            "normalized": "",
            "positive_terms": [],
            "negative_terms": [],
        }


def has_boolean_operators(query: str) -> bool:
    """Indique si la requête contient une syntaxe booléenne ou un qualificateur de champ."""
    q = (query or "").strip()
    if not q:
        return False
    return bool(
        re.search(r'(\b(AND|OR|NOT|ET|OU|SAUF)\b|[()"*]|\[[^\]]+\]|(?:ti|title|ab|abstract|tiab|au|author|jo|journal|mesh|mh|doi|pmid|tag):|\s-\S|^-\S)', q, flags=re.IGNORECASE)
    )


def build_boolean_from_blocks(
    blocks: List[Dict[str, Any]],
    exclusion_terms: Optional[List[str]] = None,
) -> str:
    """
    Construit une équation booléenne standard à partir de blocs conceptuels PICO.
    Chaque bloc : {"operator": "OR"|"AND", "field": "all"|"tiab"|..., "terms": [str, ...] | str}
    """
    block_clauses: List[str] = []
    for blk in blocks:
        if not isinstance(blk, dict):
            continue
        raw_terms = blk.get("terms") if blk.get("terms") is not None else blk.get("termsInput", "")
        if isinstance(raw_terms, str):
            terms = [t.strip() for t in re.split(r"[,;\n]+", raw_terms) if t.strip()]
        elif isinstance(raw_terms, list):
            terms = [str(t).strip() for t in raw_terms if str(t).strip()]
        else:
            terms = []
        if not terms:
            continue
        op = "AND" if str(blk.get("operator", "OR")).upper() == "AND" else "OR"
        field = normalize_field_name(str(blk.get("field", "all"))) or "all"
        formatted_terms: List[str] = []
        for t in terms:
            clean_t = t.strip().strip('"')
            has_wild = clean_t.endswith("*") and len(clean_t) >= 2
            core = clean_t[:-1].strip() if has_wild else clean_t
            piece = f'"{core}"' if (" " in core or "-" in core) else core
            if has_wild:
                piece = f"{piece}*"
            if field != "all":
                piece = f"{field}:{piece}"
            formatted_terms.append(piece)
        joined = f" {op} ".join(formatted_terms)
        block_clauses.append(f"({joined})" if len(formatted_terms) > 1 else joined)

    equation = " AND ".join(block_clauses)
    clean_exc = [str(e).strip().strip('"') for e in (exclusion_terms or []) if str(e).strip()]
    if clean_exc:
        exc_pieces = [f'"{e}"' if " " in e else e for e in clean_exc]
        exc_clause = f"({' OR '.join(exc_pieces)})" if len(exc_pieces) > 1 else exc_pieces[0]
        if equation:
            equation = f"{equation} NOT {exc_clause}"
        else:
            equation = f"NOT {exc_clause}"
    return equation


# ==============================================================================
# Compilateurs vers les API bibliographiques (PubMed, OpenAlex, S2, Crossref)
# ==============================================================================

def _render_pubmed_ast(node: BooleanAstNode, parent_op: str = "") -> str:
    if isinstance(node, TermNode):
        tag = PUBMED_FIELD_TAGS.get(node.field, "")
        core = f'"{node.value}"' if (" " in node.value or node.quoted) else node.value
        if node.wildcard:
            # PubMed supporte la troncature sans guillemets ou sur le dernier mot
            core = f"{node.value}*" if not (" " in node.value) else f'"{node.value}"'
        return f"{core}{tag}"
    if isinstance(node, NotNode):
        inner = _render_pubmed_ast(node.child, "NOT")
        return f"NOT ({inner})" if isinstance(node.child, (AndNode, OrNode)) else f"NOT {inner}"
    if isinstance(node, AndNode):
        # PubMed Entrez traite `A NOT B` comme `A NOT B` directement sans `AND` devant `NOT`
        if isinstance(node.right, NotNode):
            left_s = _render_pubmed_ast(node.left, "AND")
            right_s = _render_pubmed_ast(node.right.child, "NOT")
            if isinstance(node.right.child, (AndNode, OrNode)):
                right_s = f"({right_s})"
            expr = f"{left_s} NOT {right_s}"
        else:
            expr = f"{_render_pubmed_ast(node.left, 'AND')} AND {_render_pubmed_ast(node.right, 'AND')}"
        return f"({expr})" if parent_op in ("NOT",) else expr
    if isinstance(node, OrNode):
        expr = f"{_render_pubmed_ast(node.left, 'OR')} OR {_render_pubmed_ast(node.right, 'OR')}"
        return f"({expr})" if parent_op in ("AND", "NOT") else expr
    return ""


def compile_for_pubmed(
    query: str,
    *,
    humans_only: bool = False,
    open_access_only: bool = False,
    exclude_preprints: bool = False,
    allowed_pub_types: Optional[List[str]] = None,
    languages: Optional[List[str]] = None,
) -> str:
    """Compile une équation booléenne vers la syntaxe native NCBI PubMed Entrez."""
    base_expr = (query or "").strip()
    try:
        ast = parse_boolean_query(base_expr)
        if ast is not None:
            base_expr = _render_pubmed_ast(ast)
    except BooleanSyntaxError:
        pass

    clauses: List[str] = []
    if base_expr:
        clauses.append(f"({base_expr})")

    if allowed_pub_types:
        pt_clauses = [
            PUBMED_PUBLICATION_TYPES[pt]
            for pt in allowed_pub_types
            if pt in PUBMED_PUBLICATION_TYPES
        ]
        if pt_clauses:
            clauses.append(f"({' OR '.join(pt_clauses)})")

    if humans_only:
        clauses.append('("humans"[MeSH Terms] NOT ("animals"[MeSH Terms] NOT "humans"[MeSH Terms]))')

    if open_access_only:
        clauses.append('"loattrfree full text"[sb]')

    if languages:
        lang_clauses = [
            LANGUAGE_PUBMED_MAP[l.lower()]
            for l in languages
            if l.lower() in LANGUAGE_PUBMED_MAP
        ]
        if lang_clauses:
            clauses.append(f"({' OR '.join(lang_clauses)})")

    full_query = " AND ".join(clauses)
    if exclude_preprints and full_query:
        full_query = f'({full_query}) NOT "Preprint"[Publication Type]'
    return full_query or base_expr


def _render_openalex_ast(node: BooleanAstNode, parent_op: str = "") -> str:
    if isinstance(node, TermNode):
        # OpenAlex full-text search supporte AND / OR / NOT en majuscules, (...) et "..."
        if " " in node.value or node.quoted:
            return f'"{node.value}"'
        return node.value
    if isinstance(node, NotNode):
        inner = _render_openalex_ast(node.child, "NOT")
        return f"NOT ({inner})" if isinstance(node.child, (AndNode, OrNode)) else f"NOT {inner}"
    if isinstance(node, AndNode):
        if isinstance(node.right, NotNode):
            left_s = _render_openalex_ast(node.left, "AND")
            right_s = _render_openalex_ast(node.right.child, "NOT")
            if isinstance(node.right.child, (AndNode, OrNode)):
                right_s = f"({right_s})"
            expr = f"{left_s} NOT {right_s}"
        else:
            expr = f"{_render_openalex_ast(node.left, 'AND')} AND {_render_openalex_ast(node.right, 'AND')}"
        return f"({expr})" if parent_op in ("NOT",) else expr
    if isinstance(node, OrNode):
        expr = f"{_render_openalex_ast(node.left, 'OR')} OR {_render_openalex_ast(node.right, 'OR')}"
        return f"({expr})" if parent_op in ("AND", "NOT") else expr
    return ""


def compile_for_openalex(query: str) -> str:
    """Compile une équation booléenne vers la syntaxe `search=` OpenAlex (AND/OR/NOT, parenthèses, guillemets)."""
    raw = (query or "").strip()
    if not raw:
        return ""
    try:
        ast = parse_boolean_query(raw)
        if ast is not None:
            return _render_openalex_ast(ast)
    except BooleanSyntaxError:
        pass
    return raw


def _render_s2_bulk_ast(node: BooleanAstNode, parent_op: str = "") -> str:
    if isinstance(node, TermNode):
        core = f'"{node.value}"' if (" " in node.value or node.quoted) else node.value
        if node.wildcard and not (" " in node.value or node.quoted):
            core = f"{core}*"
        return core
    if isinstance(node, NotNode):
        inner = _render_s2_bulk_ast(node.child, "NOT")
        if isinstance(node.child, (AndNode, OrNode)):
            return f"-({inner})"
        return f"-{inner}"
    if isinstance(node, AndNode):
        if isinstance(node.right, NotNode):
            expr = f"{_render_s2_bulk_ast(node.left, 'AND')} {_render_s2_bulk_ast(node.right, 'AND')}"
        else:
            expr = f"{_render_s2_bulk_ast(node.left, 'AND')} + {_render_s2_bulk_ast(node.right, 'AND')}"
        return f"({expr})" if parent_op in ("NOT",) else expr
    if isinstance(node, OrNode):
        expr = f"{_render_s2_bulk_ast(node.left, 'OR')} | {_render_s2_bulk_ast(node.right, 'OR')}"
        return f"({expr})" if parent_op in ("AND", "NOT") else expr
    return ""


def compile_for_semantic_scholar_bulk(query: str) -> str:
    """Compile vers Semantic Scholar /paper/search/bulk (+ pour AND, | pour OR, - pour NOT, *, (), \"\")."""
    raw = (query or "").strip()
    if not raw:
        return ""
    try:
        ast = parse_boolean_query(raw)
        if ast is not None:
            return _render_s2_bulk_ast(ast)
    except BooleanSyntaxError:
        pass
    return raw


def compile_for_semantic_scholar_basic(query: str) -> str:
    """Extrait une requête simple sans opérateurs pour le repli /paper/search."""
    raw = (query or "").strip()
    try:
        ast = parse_boolean_query(raw)
        if ast is not None:
            pos, _ = _collect_terms(ast)
            words = list(dict.fromkeys(t.value for t in pos if t.value.strip()))
            if words:
                return " ".join(words[:10])
    except BooleanSyntaxError:
        pass
    cleaned = re.sub(r'\b(AND|OR|NOT|ET|OU|SAUF)\b|[()*"\[\]]', " ", raw, flags=re.IGNORECASE)
    return " ".join(cleaned.split()[:10])


def compile_for_crossref(query: str) -> Dict[str, str]:
    """Extrait les paramètres query.bibliographic / query.author / query.container-title pour Crossref."""
    raw = (query or "").strip()
    bib_terms: List[str] = []
    author_terms: List[str] = []
    journal_terms: List[str] = []
    try:
        ast = parse_boolean_query(raw)
        if ast is not None:
            pos, _ = _collect_terms(ast)
            for t in pos:
                if t.field == "au":
                    author_terms.append(t.value)
                elif t.field == "jo":
                    journal_terms.append(t.value)
                else:
                    bib_terms.append(t.value)
    except BooleanSyntaxError:
        bib_terms = [compile_for_semantic_scholar_basic(raw)]

    out: Dict[str, str] = {}
    if bib_terms:
        out["bibliographic"] = " ".join(dict.fromkeys(bib_terms))[:240]
    elif raw:
        out["bibliographic"] = compile_for_semantic_scholar_basic(raw)[:240]
    if author_terms:
        out["author"] = " ".join(dict.fromkeys(author_terms))[:120]
    if journal_terms:
        out["container_title"] = " ".join(dict.fromkeys(journal_terms))[:120]
    return out


def compile_for_pedro_pubmed(
    query: str,
    *,
    subdiscipline: str = "",
    therapy: str = "",
    humans_only: bool = True,
    open_access_only: bool = False,
    languages: Optional[List[str]] = None,
) -> str:
    """
    Compile une requête booléenne pour le périmètre PEDro (Physiotherapy Evidence Database)
    sur PubMed Entrez : essais cliniques randomisés / revues systématiques / guides + MeSH Physiothérapie.
    """
    pedro_methods = (
        '("Randomized Controlled Trial"[Publication Type] OR '
        '"Controlled Clinical Trial"[Publication Type] OR '
        '"Systematic Review"[Publication Type] OR '
        '"Meta-Analysis"[Publication Type] OR '
        '"Practice Guideline"[Publication Type] OR '
        '"Guideline"[Publication Type])'
    )
    pedro_scope = (
        '("Physical Therapy Modalities"[MeSH Terms] OR '
        '"Rehabilitation"[MeSH Terms] OR '
        '"Exercise Therapy"[MeSH Terms] OR '
        '"Musculoskeletal Manipulations"[MeSH Terms] OR '
        '"Athletic Injuries"[MeSH Terms] OR '
        '"Recovery of Function"[MeSH Terms] OR '
        'physiotherap*[Title/Abstract] OR '
        '"physical therapy"[Title/Abstract] OR '
        'rehabilitat*[Title/Abstract] OR '
        '"exercise therapy"[Title/Abstract] OR '
        '"injury prevention"[Title/Abstract] OR '
        'tendinopath*[Title/Abstract] OR '
        'eccentric[Title/Abstract] OR '
        'neuromuscular[Title/Abstract])'
    )

    base = compile_for_pubmed(
        query,
        humans_only=humans_only,
        open_access_only=open_access_only,
        exclude_preprints=True,
        languages=languages,
    )
    parts = [f"({base})" if base else "", pedro_methods, pedro_scope]
    if subdiscipline and subdiscipline in PEDRO_SUBDISCIPLINES:
        parts.append(PEDRO_SUBDISCIPLINES[subdiscipline]["pubmed"])
    if therapy and therapy in PEDRO_THERAPIES:
        parts.append(PEDRO_THERAPIES[therapy]["pubmed"])
    return " AND ".join(p for p in parts if p)


def build_pedro_advanced_search_url(
    query: str,
    *,
    start_year: Optional[int] = None,
    subdiscipline: str = "",
    therapy: str = "",
    min_pedro_score: int = 0,
    allowed_pub_types: Optional[List[str]] = None,
    per_page: int = 20,
) -> str:
    """
    Génère l'URL GET officielle vers `https://search.pedro.org.au/advanced-search/results`.
    Respecte la validation stricte de PEDro : ASCII uniquement, pas d'opérateurs AND/OR/NOT ni parenthèses
    dans les champs texte, champ dédié `title` / `authors_association` / `source`, et codes VL013xx.
    """
    raw = (query or "").strip()
    abs_title_terms: List[str] = []
    title_terms: List[str] = []
    author_terms: List[str] = []
    source_terms: List[str] = []
    lop = "and"

    try:
        ast = parse_boolean_query(raw)
        if ast is not None:
            if isinstance(ast, OrNode):
                lop = "or"
            pos, _ = _collect_terms(ast)
            for t in pos:
                ascii_val = re.sub(r"[^\x20-\x7E]", " ", t.value).strip()
                ascii_val = re.sub(r"\b(and|or|not)\b", " ", ascii_val, flags=re.IGNORECASE)
                ascii_val = " ".join(ascii_val.split())
                if len(ascii_val) < 3:
                    continue
                token = f"{ascii_val}*" if t.wildcard and not ascii_val.endswith("*") else ascii_val
                if t.field == "ti":
                    title_terms.append(token)
                elif t.field == "au":
                    author_terms.append(token)
                elif t.field == "jo":
                    source_terms.append(token)
                else:
                    abs_title_terms.append(token)
    except BooleanSyntaxError:
        cleaned = re.sub(r"[^\x20-\x7E]", " ", compile_for_semantic_scholar_basic(raw))
        cleaned = " ".join(cleaned.split())
        if len(cleaned) >= 3:
            abs_title_terms.append(cleaned)

    params: Dict[str, str] = {
        "perpage": str(per_page if per_page in (5, 10, 20, 30, 50) else 20),
        "lop": lop,
        "find": "Start Search",
    }
    if abs_title_terms:
        params["abstract_with_title"] = " ".join(dict.fromkeys(abs_title_terms))[:140]
    if title_terms:
        params["title"] = " ".join(dict.fromkeys(title_terms))[:100]
    if author_terms:
        params["authors_association"] = " ".join(dict.fromkeys(author_terms))[:100]
    if source_terms:
        params["source"] = " ".join(dict.fromkeys(source_terms))[:100]
    if start_year and 1900 <= start_year <= 3000:
        params["year_of_publication"] = str(start_year)
    if subdiscipline and subdiscipline in PEDRO_SUBDISCIPLINES:
        params["subdiscipline"] = PEDRO_SUBDISCIPLINES[subdiscipline]["code"]
    if therapy and therapy in PEDRO_THERAPIES:
        params["therapy"] = PEDRO_THERAPIES[therapy]["code"]
    if min_pedro_score and 1 <= min_pedro_score <= 10:
        params["nscore"] = str(min_pedro_score)

    if allowed_pub_types:
        pt_set = set(allowed_pub_types)
        if pt_set.issubset({"systematic_review", "meta_analysis"}):
            params["method"] = "systematic review"
        elif pt_set == {"consensus_statement"}:
            params["method"] = "practice guideline"
        elif pt_set.issubset({"randomized_controlled_trial", "controlled_trial"}):
            params["method"] = "clinical trial"

    return f"https://search.pedro.org.au/advanced-search/results?{urllib.parse.urlencode(params)}"


# ==============================================================================
# Évaluateur en mémoire sur une publication (corpus local & filtre post-collecte)
# ==============================================================================

def _get_attr_or_key(obj: Any, name: str, default: Any = "") -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _extract_field_haystacks(target: Any) -> Dict[str, str]:
    title = str(_get_attr_or_key(target, "title", "") or "")
    abstract = str(_get_attr_or_key(target, "abstract", "") or "")
    summary_fr = str(_get_attr_or_key(target, "summary_fr", "") or "")
    takeaway = str(_get_attr_or_key(target, "practical_takeaway", "") or "")
    journal = str(_get_attr_or_key(target, "journal", "") or "")
    doi = str(_get_attr_or_key(target, "doi", "") or "")
    pmid = str(_get_attr_or_key(target, "pmid", "") or "")

    authors_raw = _get_attr_or_key(target, "authors", []) or []
    authors = " ".join(str(a) for a in authors_raw) if isinstance(authors_raw, list) else str(authors_raw)

    mesh_raw = _get_attr_or_key(target, "mesh_terms", []) or []
    concepts_raw = _get_attr_or_key(target, "concepts", []) or []
    tags_raw = _get_attr_or_key(target, "tags", []) or []
    key_findings_raw = _get_attr_or_key(target, "key_findings", []) or []

    mesh = " ".join(str(m) for m in (list(mesh_raw) + list(concepts_raw)))
    tags = " ".join(str(t) for t in tags_raw)
    findings = " ".join(str(f) for f in key_findings_raw)
    theme_label = str(_get_attr_or_key(target, "primary_theme_label", "") or "")

    ab_full = f"{abstract} {summary_fr} {takeaway} {findings}".strip()
    all_full = f"{title} {ab_full} {authors} {journal} {mesh} {tags} {theme_label} {doi} {pmid}".strip()

    return {
        "ti": title.lower(),
        "ab": ab_full.lower(),
        "tiab": f"{title} {ab_full}".lower(),
        "au": authors.lower(),
        "jo": journal.lower(),
        "mesh": mesh.lower(),
        "doi": doi.lower(),
        "pmid": pmid.lower(),
        "tag": f"{tags} {theme_label}".lower(),
        "all": all_full.lower(),
    }


def _match_term(term: TermNode, haystacks: Dict[str, str]) -> bool:
    needle = term.value.strip().lower()
    if not needle:
        return True
    hay = haystacks.get(term.field, haystacks["all"])
    if not hay:
        return False

    if term.field in ("doi", "pmid"):
        return needle in hay

    # Troncature préfixe (cardio*)
    if term.wildcard:
        escaped = re.escape(needle).replace(r"\ ", r"[\s-]+")
        pattern = rf"(?<!\w){escaped}\w*"
        return bool(re.search(pattern, hay))

    # Expression exacte ou mot complet (avec tolérance espace/tiret sur expressions multi-mots)
    escaped = re.escape(needle).replace(r"\ ", r"[\s-]+").replace(r"\-", r"[\s-]+")
    if term.quoted or " " in needle:
        pattern = rf"(?<!\w){escaped}(?!\w)"
        return bool(re.search(pattern, hay))

    # Mot simple : correspondance par limite de mot au début (tolère pluriels/suffixes si >= 5 car? Non, strict mot ou sous-chaîne pour CJK/DOI)
    pattern = rf"(?<!\w){escaped}(?!\w)"
    if re.search(pattern, hay):
        return True
    # Tolérance légère sur pluriel simple anglais/français (+s) pour mots non-tronqués >= 4 car.
    if len(needle) >= 4 and re.search(rf"(?<!\w){escaped}s(?!\w)", hay):
        return True
    return False


def evaluate_ast(node: Optional[BooleanAstNode], haystacks: Dict[str, str]) -> bool:
    if node is None:
        return True
    if isinstance(node, TermNode):
        return _match_term(node, haystacks)
    if isinstance(node, NotNode):
        return not evaluate_ast(node.child, haystacks)
    if isinstance(node, AndNode):
        return evaluate_ast(node.left, haystacks) and evaluate_ast(node.right, haystacks)
    if isinstance(node, OrNode):
        return evaluate_ast(node.left, haystacks) or evaluate_ast(node.right, haystacks)
    return True


def matches_boolean_query(target: Any, query_or_ast: Union[str, BooleanAstNode, None]) -> bool:
    """Évalue si une publication satisfait une équation booléenne ou AST."""
    if query_or_ast is None:
        return True
    if isinstance(query_or_ast, str):
        stripped = query_or_ast.strip()
        if not stripped:
            return True
        try:
            ast = parse_boolean_query(stripped)
        except BooleanSyntaxError:
            haystacks = _extract_field_haystacks(target)
            return stripped.lower() in haystacks["all"]
    else:
        ast = query_or_ast

    if ast is None:
        return True
    haystacks = _extract_field_haystacks(target)
    return evaluate_ast(ast, haystacks)
