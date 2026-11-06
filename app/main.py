import json
import pickle
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.feature_extractor import FEATURE_COLUMNS, extract_features, normalize_url


PROJECT_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_DIR / 'models' / 'phishing_url_model.pkl'
METADATA_PATH = PROJECT_DIR / 'models' / 'phishing_url_metadata.json'

with MODEL_PATH.open('rb') as model_file:
    model = pickle.load(model_file)
metadata = json.loads(METADATA_PATH.read_text(encoding='utf-8'))
feature_columns = metadata['feature_columns']
labels = {int(label): name for label, name in metadata['labels'].items()}

if len(feature_columns) != len(FEATURE_COLUMNS) or set(feature_columns) != set(FEATURE_COLUMNS):
    raise ValueError('Fitur pada metadata tidak sesuai dengan app/feature_extractor.py.')
if list(model.feature_names_in_) != feature_columns:
    raise ValueError('Urutan fitur model tidak sesuai dengan metadata.')
if set(model.classes_) != {0, 1} or labels != {0: 'Phishing', 1: 'Legitimate'}:
    raise ValueError('Model dan metadata harus memakai label 0=Phishing, 1=Legitimate.')

MODEL_CONTEXT = {
    'model_name': metadata['selected_model'],
    'feature_count': len(feature_columns),
    'evaluation_metrics': {
        name: round(float(value) * 100, 2)
        for name, value in metadata['test_metrics'].items()
    },
}

app = FastAPI(title='Phishing URL Detection')
templates = Jinja2Templates(directory=str(PROJECT_DIR / 'app' / 'templates'))


def render_page(request, *, status_code=200, **context):
    return templates.TemplateResponse(
        request=request,
        name='index.html',
        context={**MODEL_CONTEXT, 'url': '', 'result': None, 'error': None, **context},
        status_code=status_code,
    )


@app.get('/', response_class=HTMLResponse)
def home(request: Request):
    return render_page(request)


@app.post('/predict', response_class=HTMLResponse)
def predict(request: Request, url: str = Form('')):
    submitted_url = url.strip()
    try:
        normalized = normalize_url(submitted_url)
        parsed = urlparse(normalized)
        if (not submitted_url or parsed.scheme not in {'http', 'https'}
                or not parsed.hostname or any(char.isspace() for char in normalized)):
            raise ValueError('Invalid URL')
        # Accessing port also checks invalid and out-of-range port numbers.
        _ = parsed.port
        features = extract_features(normalized)
    except ValueError:
        return render_page(
            request, status_code=400, url=submitted_url,
            error='Enter a valid HTTP or HTTPS URL, for example https://example.com.',
        )

    features_df = pd.DataFrame([features], columns=feature_columns)
    prediction = int(model.predict(features_df)[0])
    probabilities = model.predict_proba(features_df)[0]
    class_order = list(model.classes_)
    risk_score = round(float(probabilities[class_order.index(0)]) * 100, 2)
    confidence_score = round(float(probabilities[class_order.index(prediction)]) * 100, 2)

    domain = parsed.hostname
    domain_parts = domain.split('.')
    tld = ('.' + domain_parts[-1]
           if not features['IsDomainIP'] and len(domain_parts) > 1 else 'N/A')

    return render_page(
        request,
        url=submitted_url,
        normalized_url=normalized,
        result=labels[prediction],
        risk_score=risk_score,
        confidence_score=confidence_score,
        display_https='Yes' if features['IsHTTPS'] else 'No',
        display_url_length=features['URLLength'],
        display_domain_length=features['DomainLength'],
        display_subdomains=features['NoOfSubDomain'],
        display_tld=tld,
        display_digits=features['NoOfDegitsInURL'],
        display_special_chars=features['NoOfOtherSpecialCharsInURL'],
        display_domain=domain,
    )
