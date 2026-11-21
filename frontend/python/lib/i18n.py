"""Translations and a simple I18n class (port of src/lib/i18n.tsx, without React)."""
from __future__ import annotations

import json
import os
from typing import Literal, Optional, TypedDict

Lang = Literal["en", "te"]

EN: dict[str, str] = {'language': 'Language',
 'diagnoseLeaf': 'Diagnose Leaf',
 'gradeProduce': 'Grade Produce',
 'identifyPest': 'Identify Pest',
 'newAnalysis': 'New analysis',
 'addPhoto': 'Add your photo',
 'tipLeaf': 'Photograph the affected leaf area in good natural light. Fill the frame with the leaf.',
 'tipProduce': 'Photograph the whole piece of fruit against a plain background.',
 'tipPest': 'Photograph the insect or the damaged area up close in good light. Keep the pest in focus.',
 'photoHere': 'Your photo will appear here',
 'bestResults': 'Best results: bright daylight, no blur, avoid heavy shadows on the subject.',
 'upload': 'Upload Photo',
 'takePhoto': 'Take Photo',
 'camTipLeaf': 'Fill the frame with the leaf',
 'camTipFruit': 'Plain background for fruit',
 'camTipPest': 'Get close and keep the pest in focus',
 'camTipLight': 'Use daylight and hold steady',
 'capture': 'Capture photo',
 'cancel': 'Cancel',
 'camStarting': 'Starting camera…',
 'camUnavailable': "The camera isn't available here. You can upload a photo instead.",
 'camUseUpload': 'Upload a photo instead',
 'camGuide': 'Frame guide: place the subject inside the box',
 'analysing': 'Analysing…',
 'analysingSlow': 'Still analysing… almost there.',
 'submittedPhoto': 'Your submitted photo',
 'result': 'Result',
 'notSure': 'Not sure yet',
 'lowConf': "I'm not sure. Try a closer, sharper photo in daylight",
 'retake': 'Retake photo',
 'confidence': 'confidence',
 'closest': 'Closest guess',
 'top3': 'Top 3 guesses',
 'compare': 'Photo vs heatmap',
 'compareHint': 'Drag to compare the photo with the heatmap',
 'photo': 'Photo',
 'heatmap': 'Heatmap',
 'compareCaption': 'Red areas influenced the result most',
 'photoAlt': 'Photo you submitted',
 'heatmapAlt': 'Heatmap overlay on your photo; red areas influenced the result most',
 'about': 'About this result',
 'cleanAcc': 'Accuracy on clean images',
 'fieldAcc': 'Accuracy on field photos',
 'fruit': 'Fruit',
 'condition': 'Condition',
 'fresh': 'Fresh',
 'rotten': 'Rotten',
 'healthy': 'Healthy',
 'disease': 'Disease detected',
 'treatment': 'Suggested treatment',
 'source': 'Source',
 'tryAnother': 'Try Another Photo',
 'mistakes': "FarmSight can make mistakes and can't be 100% sure about any result. Use this as a guide and confirm important "
             'decisions with an expert.',
 'errUnreadable': "Couldn't read that image",
 'errUnreadableBody': 'The file may be damaged or not a photo. Choose another image and try again.',
 'errEmpty': 'No photo to analyse',
 'errEmptyBody': "We didn't get an image or a result. Add a photo to start.",
 'errNetwork': "Can't reach the analysis service",
 'errNetworkBody': 'Check your connection and try again.',
 'errServer': 'Something went wrong',
 'errServerBody': 'The analysis did not finish. Please try again in a moment.',
 'tryAgain': 'Try again',
 'chooseAnother': 'Choose another photo'}

TE: dict[str, str] = {'language': 'భాష',
 'diagnoseLeaf': 'ఆకు వ్యాధి గుర్తింపు',
 'gradeProduce': 'పంట నాణ్యత గ్రేడింగ్',
 'identifyPest': 'చీడపురుగు గుర్తింపు',
 'newAnalysis': 'కొత్త విశ్లేషణ',
 'addPhoto': 'మీ ఫోటోను జోడించండి',
 'tipLeaf': 'ప్రభావిత ఆకు భాగాన్ని మంచి సహజ వెలుతురులో ఫోటో తీయండి. ఫ్రేమ్ నిండా ఆకు ఉండాలి.',
 'tipProduce': 'సాదా నేపథ్యంలో మొత్తం పండును ఫోటో తీయండి.',
 'tipPest': 'పురుగును లేదా దెబ్బతిన్న భాగాన్ని మంచి వెలుతురులో దగ్గరగా ఫోటో తీయండి. పురుగు స్పష్టంగా ఉండాలి.',
 'photoHere': 'మీ ఫోటో ఇక్కడ కనిపిస్తుంది',
 'bestResults': 'మెరుగైన ఫలితాల కోసం: పగటి వెలుతురు, బ్లర్ లేకుండా, గాఢమైన నీడలు లేకుండా చూడండి.',
 'upload': 'ఫోటో అప్\u200cలోడ్ చేయండి',
 'takePhoto': 'ఫోటో తీయండి',
 'camTipLeaf': 'ఫ్రేమ్ నిండా ఆకు ఉంచండి',
 'camTipFruit': 'పండుకు సాదా నేపథ్యం వాడండి',
 'camTipPest': 'దగ్గరగా వెళ్లి పురుగు స్పష్టంగా ఉంచండి',
 'camTipLight': 'పగటి వెలుతురులో, కెమెరాను స్థిరంగా పట్టుకోండి',
 'capture': 'ఫోటో తీయండి',
 'cancel': 'రద్దు',
 'camStarting': 'కెమెరా ప్రారంభమవుతోంది…',
 'camUnavailable': 'ఇక్కడ కెమెరా అందుబాటులో లేదు. బదులుగా ఫోటో అప్\u200cలోడ్ చేయవచ్చు.',
 'camUseUpload': 'బదులుగా ఫోటో అప్\u200cలోడ్ చేయండి',
 'camGuide': 'ఫ్రేమ్ గైడ్: వస్తువును పెట్టె లోపల ఉంచండి',
 'analysing': 'విశ్లేషిస్తోంది…',
 'analysingSlow': 'ఇంకా విశ్లేషిస్తోంది… దాదాపు పూర్తయింది.',
 'submittedPhoto': 'మీరు పంపిన ఫోటో',
 'result': 'ఫలితం',
 'notSure': 'ఇంకా ఖచ్చితంగా తెలియదు',
 'lowConf': 'నాకు ఖచ్చితంగా తెలియదు. పగటి వెలుతురులో దగ్గరగా, స్పష్టంగా మరో ఫోటో తీయండి',
 'retake': 'మళ్ళీ ఫోటో తీయండి',
 'confidence': 'నమ్మకం',
 'closest': 'దగ్గరి అంచనా',
 'top3': 'టాప్ 3 అంచనాలు',
 'compare': 'ఫోటో మరియు హీట్\u200cమ్యాప్',
 'compareHint': 'ఫోటోను హీట్\u200cమ్యాప్\u200cతో పోల్చడానికి లాగండి',
 'photo': 'ఫోటో',
 'heatmap': 'హీట్\u200cమ్యాప్',
 'compareCaption': 'ఎరుపు ప్రాంతాలు ఫలితంపై ఎక్కువ ప్రభావం చూపాయి',
 'photoAlt': 'మీరు పంపిన ఫోటో',
 'heatmapAlt': 'మీ ఫోటోపై హీట్\u200cమ్యాప్; ఎరుపు ప్రాంతాలు ఫలితంపై ఎక్కువ ప్రభావం చూపాయి',
 'about': 'ఈ ఫలితం గురించి',
 'cleanAcc': 'స్పష్టమైన చిత్రాలపై ఖచ్చితత్వం',
 'fieldAcc': 'పొలం ఫోటోలపై ఖచ్చితత్వం',
 'fruit': 'పండు',
 'condition': 'స్థితి',
 'fresh': 'తాజా',
 'rotten': 'కుళ్ళిన',
 'healthy': 'ఆరోగ్యంగా ఉంది',
 'disease': 'వ్యాధి గుర్తించబడింది',
 'treatment': 'సూచించిన చికిత్స',
 'source': 'మూలం',
 'tryAnother': 'మరో ఫోటో ప్రయత్నించండి',
 'mistakes': 'FarmSight తప్పులు చేయవచ్చు, ఏ ఫలితం గురించీ 100% ఖచ్చితంగా చెప్పలేదు. దీన్ని ఒక మార్గదర్శిగా వాడండి, ముఖ్యమైన '
             'నిర్ణయాలను నిపుణులతో నిర్ధారించుకోండి.',
 'errUnreadable': 'ఆ చిత్రాన్ని చదవలేకపోయాం',
 'errUnreadableBody': 'ఫైల్ పాడై ఉండవచ్చు లేదా ఫోటో కాకపోవచ్చు. మరో చిత్రాన్ని ఎంచుకొని మళ్ళీ ప్రయత్నించండి.',
 'errEmpty': 'విశ్లేషించడానికి ఫోటో లేదు',
 'errEmptyBody': 'చిత్రం లేదా ఫలితం అందలేదు. ప్రారంభించడానికి ఫోటో జోడించండి.',
 'errNetwork': 'విశ్లేషణ సేవను చేరుకోలేకపోయాం',
 'errNetworkBody': 'మీ కనెక్షన్ చూసి మళ్ళీ ప్రయత్నించండి.',
 'errServer': 'ఏదో తప్పు జరిగింది',
 'errServerBody': 'విశ్లేషణ పూర్తి కాలేదు. కొద్దిసేపటి తర్వాత మళ్ళీ ప్రయత్నించండి.',
 'tryAgain': 'మళ్ళీ ప్రయత్నించండి',
 'chooseAnother': 'మరో ఫోటో ఎంచుకోండి'}

DICT: dict[str, dict[str, str]] = {"en": EN, "te": TE}

LANG_STORAGE_KEY = "farmsight.lang"
LANG_FILE = os.environ.get("FARMSIGHT_LANG_FILE", os.path.join(os.path.expanduser("~"), ".farmsight_lang.json"))


class LangOption(TypedDict):
    id: str
    label: str
    name: str


# Options shown by the language toggle.
LANG_OPTIONS: list[LangOption] = [
    {"id": "en", "label": "EN", "name": "English"},
    {"id": "te", "label": "తెలుగు", "name": "తెలుగు"},
]


class I18n:
    """Replacement for LangProvider/useT: holds the language, persists it to a JSON file."""

    def __init__(self, path: Optional[str] = LANG_FILE, persist: bool = False) -> None:
        self._path = path
        self._persist = persist
        self.lang: str = self._load()

    def _load(self) -> str:
        if not self._persist or not self._path:
            return "en"
        try:
            with open(self._path, encoding="utf-8") as f:
                return "te" if json.load(f).get(LANG_STORAGE_KEY) == "te" else "en"
        except (OSError, ValueError, AttributeError):
            return "en"

    def set_lang(self, lang: str) -> None:
        if lang not in DICT:
            raise ValueError(f"unsupported language: {lang}")
        self.lang = lang
        if self._persist and self._path:
            try:
                with open(self._path, "w", encoding="utf-8") as f:
                    json.dump({LANG_STORAGE_KEY: lang}, f)
            except OSError:
                pass  # storage unavailable

    def t(self, key: str) -> str:
        return DICT[self.lang][key]


i18n = I18n()


def use_t() -> I18n:
    return i18n


def lang_provider(children):
    return children


def lang_toggle(on_dark: bool = False) -> str:
    from python.h import h

    wrap = "bg-white/20" if on_dark else "bg-[#E8E4DB]"
    buttons = []
    for o in LANG_OPTIONS:
        on = i18n.lang == o["id"]
        tone = (
            "bg-[#2D6A4F] text-white" if on
            else "text-white hover:bg-white/10" if on_dark
            else "text-[#2D4A3A] hover:bg-[#DDD8CE]"
        )
        buttons.append(h("button", {
            "data_action": "set-lang", "data_lang": o["id"], "aria_pressed": str(on).lower(),
            "lang": o["id"], "aria_label": o["name"],
            "class_": f"min-w-11 min-h-11 px-3 rounded-full text-sm font-bold transition-colors {tone}",
            "style": "font-family: Manrope, sans-serif",
        }, o["label"]))
    return h("div", {"role": "group", "aria_label": i18n.t("language"),
                     "class_": f"inline-flex rounded-full p-0.5 {wrap}"}, *buttons)
