"""
design_api.py
=============
REST API endpoints for the Design Engine
Provides Gemini with programmatic access to design rules and recommendations
"""

from flask import Flask, request, jsonify
import json
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from schema_rules import (
        detect_mood_from_keywords,
        detect_domain_from_keywords,
        recommend_surface_for_block,
        recommend_theme_for_mood,
        get_recommended_blocks,
        validate_page_schema,
        VALID_MOODS,
        VALID_DOMAINS,
        VALID_THEMES,
        SURFACE_TYPES,
        BLOCK_LIBRARY,
    )
except ImportError:
    # Fallback definitions for testing
    VALID_MOODS = ["modern", "professional", "educational", "playful", "minimal", "luxurious"]
    VALID_DOMAINS = ["marketing", "education", "product", "service", "portfolio", "documentation", "community"]
    VALID_THEMES = ["default", "future-purple", "alexandros"]
    SURFACE_TYPES = ["flat", "glass", "neumorphism", "bordered", "elevated", "paper", "glow", "frosted-dark"]
    BLOCK_LIBRARY = {}

app = Flask(__name__)

# Load design manifest
manifest_path = Path(__file__).parent.parent / "block-library" / "design-manifest.json"
DESIGN_MANIFEST = {}
if manifest_path.exists():
    with open(manifest_path) as f:
        DESIGN_MANIFEST = json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# Intent Detection Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/design/intent', methods=['POST'])
def detect_intent_endpoint():
    """
    Detect mood and domain from user input text
    
    POST /api/design/intent
    Content-Type: application/json
    {
        "description": "モダンな紫色テーマでReactチュートリアル作成"
    }
    """
    data = request.get_json() or {}
    description = data.get('description', '')
    
    if not description:
        return jsonify({
            'error': 'description field is required',
            'example': {'description': 'Create a modern React tutorial'}
        }), 400
    
    try:
        mood = detect_mood_from_keywords(description)
        domain = detect_domain_from_keywords(description)
    except:
        mood = "professional"
        domain = "education"
    
    return jsonify({
        'status': 'success',
        'mood': mood,
        'domain': domain,
        'input': description
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# Design Suggestion Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/design/suggest', methods=['POST'])
def suggest_design_endpoint():
    """
    Generate design recommendations based on mood and domain
    
    POST /api/design/suggest
    Content-Type: application/json
    {
        "description": "モダンな紫色テーマでReactチュートリアル作成"
    }
    """
    data = request.get_json() or {}
    description = data.get('description', '')
    
    if not description:
        return jsonify({'error': 'description field is required'}), 400
    
    try:
        mood = data.get('mood') or detect_mood_from_keywords(description)
        domain = data.get('domain') or detect_domain_from_keywords(description)
        recommended_theme = recommend_theme_for_mood(mood)
        recommended_blocks = get_recommended_blocks(domain, limit=8)
    except:
        mood = "professional"
        domain = "education"
        recommended_theme = "default"
        recommended_blocks = list(BLOCK_LIBRARY.keys())[:8]
    
    # Surface recommendations per block
    surface_recs = {}
    for block in recommended_blocks:
        try:
            surface_recs[block] = recommend_surface_for_block(block, mood)
        except:
            surface_recs[block] = "flat"
    
    return jsonify({
        'status': 'success',
        'mood': mood,
        'domain': domain,
        'recommended_theme': recommended_theme,
        'recommended_blocks': recommended_blocks,
        'surface_recommendations': surface_recs,
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# Design Manifest Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/design/manifest', methods=['GET'])
def get_manifest_endpoint():
    """Get complete design manifest"""
    return jsonify(DESIGN_MANIFEST), 200


# ─────────────────────────────────────────────────────────────────────────────
# Block Library Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/design/blocks', methods=['GET'])
def list_blocks_endpoint():
    """
    List all available blocks with variants
    
    GET /api/design/blocks
    """
    blocks = []
    for block_type, variants in BLOCK_LIBRARY.items():
        blocks.append({
            'type': block_type,
            'variants': variants
        })
    
    return jsonify({
        'status': 'success',
        'total': len(blocks),
        'blocks': blocks
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# Surface Types Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/design/surfaces', methods=['GET'])
def list_surfaces_endpoint():
    """
    List all available surface types
    
    GET /api/design/surfaces
    """
    return jsonify({
        'status': 'success',
        'surfaces': SURFACE_TYPES
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# Theme Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/design/themes', methods=['GET'])
def list_themes_endpoint():
    """
    List all available themes
    
    GET /api/design/themes
    """
    return jsonify({
        'status': 'success',
        'themes': list(VALID_THEMES)
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# Schema Validation Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/design/validate', methods=['POST'])
def validate_schema_endpoint():
    """
    Validate a page schema against design rules
    
    POST /api/design/validate
    Content-Type: application/json
    {
        "schema": {
            "page": { "theme": "future-purple", ... },
            "blocks": [...]
        }
    }
    """
    data = request.get_json() or {}
    schema = data.get('schema')
    
    if not schema:
        return jsonify({'error': 'schema field is required'}), 400
    
    try:
        errors = validate_page_schema(schema)
        if errors:
            return jsonify({
                'valid': False,
                'errors': errors
            }), 400
    except Exception as e:
        return jsonify({
            'valid': False,
            'error': str(e)
        }), 400
    
    return jsonify({
        'valid': True,
        'message': 'Schema is valid'
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# Health Check Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/design/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'valid_moods': VALID_MOODS,
        'valid_domains': VALID_DOMAINS,
        'valid_themes': list(VALID_THEMES),
        'surface_types': SURFACE_TYPES,
        'total_blocks': len(BLOCK_LIBRARY)
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# Error Handlers
# ─────────────────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
