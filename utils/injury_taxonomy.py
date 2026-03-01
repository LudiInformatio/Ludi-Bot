"""
Ludi-Bot Injury Taxonomy
Phase 8 Module D Overhaul
"""

INJURY_TAXONOMY = {
    'ACTIVE': {
        'category': 'AVAILABLE',
        'display_name': 'Active',
        'severity_score': 0,
        'sim_multiplier': 1.0,
        'usage_vacuum_trigger': False,
        'confidence_decay_hours': 48,
        'edge_type': 'base',
        'actionable': True
    },
    'PROBABLE': {
        'category': 'AVAILABLE',
        'display_name': 'Probable',
        'severity_score': 0,
        'sim_multiplier': 1.0,
        'usage_vacuum_trigger': False,
        'confidence_decay_hours': 24,
        'edge_type': 'base',
        'actionable': True
    },
    'MINUTES_LIMIT': {
        'category': 'RESTRICTED',
        'display_name': 'Minutes Limit',
        'severity_score': 1,
        'sim_multiplier': 0.6,
        'usage_vacuum_trigger': True,
        'confidence_decay_hours': 12,
        'edge_type': 'under',
        'actionable': True
    },
    'GTD': {
        'category': 'UNCERTAIN',
        'display_name': 'Game Time Decision',
        'severity_score': 1,
        'sim_multiplier': 0.5,
        'usage_vacuum_trigger': False,
        'confidence_decay_hours': 6,
        'edge_type': 'avoid',
        'actionable': False
    },
    'QUESTIONABLE': {
        'category': 'UNCERTAIN',
        'display_name': 'Questionable',
        'severity_score': 1,
        'sim_multiplier': 0.5,
        'usage_vacuum_trigger': False,
        'confidence_decay_hours': 12,
        'edge_type': 'avoid',
        'actionable': False
    },
    'DOUBTFUL': {
        'category': 'UNCERTAIN',
        'display_name': 'Doubtful',
        'severity_score': 2,
        'sim_multiplier': 0.0,
        'usage_vacuum_trigger': True,
        'confidence_decay_hours': 24,
        'edge_type': 'vacuum',
        'actionable': True
    },
    'OUT': {
        'category': 'UNAVAILABLE',
        'display_name': 'Out',
        'severity_score': 3,
        'sim_multiplier': 0.0,
        'usage_vacuum_trigger': True,
        'confidence_decay_hours': 72,
        'edge_type': 'vacuum',
        'actionable': True
    },
    'OUT_REST': {
        'category': 'UNAVAILABLE',
        'display_name': 'Out (Rest)',
        'severity_score': 3,
        'sim_multiplier': 0.0,
        'usage_vacuum_trigger': True,
        'confidence_decay_hours': 48,
        'edge_type': 'vacuum',
        'actionable': True
    },
    'SUSP': {
        'category': 'UNAVAILABLE',
        'display_name': 'Suspended',
        'severity_score': 3,
        'sim_multiplier': 0.0,
        'usage_vacuum_trigger': True,
        'confidence_decay_hours': 120,
        'edge_type': 'vacuum',
        'actionable': True
    },
    'SEASON_ENDING': {
        'category': 'UNAVAILABLE',
        'display_name': 'Season Ending',
        'severity_score': 3,
        'sim_multiplier': 0.0,
        'usage_vacuum_trigger': True,
        'confidence_decay_hours': 9999,
        'edge_type': 'vacuum',
        'actionable': True
    }
}

INJURY_LANGUAGE_MAP = [
    # ESPN exact codes
    {'source': 'ESPN', 'source_phrase': 'Out', 'canonical_status': 'OUT', 'parse_type': 'exact', 'confidence': 1.0},
    {'source': 'ESPN', 'source_phrase': 'Questionable', 'canonical_status': 'GTD', 'parse_type': 'exact', 'confidence': 1.0},
    {'source': 'ESPN', 'source_phrase': 'Doubtful', 'canonical_status': 'DOUBTFUL', 'parse_type': 'exact', 'confidence': 1.0},
    {'source': 'ESPN', 'source_phrase': 'Day-To-Day', 'canonical_status': 'GTD', 'parse_type': 'exact', 'confidence': 1.0},
    {'source': 'ESPN', 'source_phrase': 'Probable', 'canonical_status': 'PROBABLE', 'parse_type': 'exact', 'confidence': 1.0},
    # Tank01 exact codes
    {'source': 'Tank01', 'source_phrase': 'Out', 'canonical_status': 'OUT', 'parse_type': 'exact', 'confidence': 0.9},
    {'source': 'Tank01', 'source_phrase': 'Questionable', 'canonical_status': 'QUESTIONABLE', 'parse_type': 'exact', 'confidence': 0.9},
    {'source': 'Tank01', 'source_phrase': 'Doubtful', 'canonical_status': 'DOUBTFUL', 'parse_type': 'exact', 'confidence': 0.9},
    {'source': 'Tank01', 'source_phrase': 'Day-To-Day', 'canonical_status': 'GTD', 'parse_type': 'exact', 'confidence': 0.9},
    {'source': 'Tank01', 'source_phrase': 'Probable', 'canonical_status': 'PROBABLE', 'parse_type': 'exact', 'confidence': 0.9},
    {'source': 'Tank01', 'source_phrase': 'Available', 'canonical_status': 'ACTIVE', 'parse_type': 'exact', 'confidence': 0.9},
    # BDL exact codes
    {'source': 'BDL', 'source_phrase': 'Out', 'canonical_status': 'OUT', 'parse_type': 'exact', 'confidence': 0.8},
    {'source': 'BDL', 'source_phrase': 'Questionable', 'canonical_status': 'QUESTIONABLE', 'parse_type': 'exact', 'confidence': 0.8},
    {'source': 'BDL', 'source_phrase': 'Doubtful', 'canonical_status': 'DOUBTFUL', 'parse_type': 'exact', 'confidence': 0.8},
    {'source': 'BDL', 'source_phrase': 'Day-To-Day', 'canonical_status': 'GTD', 'parse_type': 'exact', 'confidence': 0.8},
    {'source': 'BDL', 'source_phrase': 'Probable', 'canonical_status': 'PROBABLE', 'parse_type': 'exact', 'confidence': 0.8},
    {'source': 'BDL', 'source_phrase': 'Suspended', 'canonical_status': 'SUSP', 'parse_type': 'exact', 'confidence': 0.9},
    # RotoWire keywords
    {'source': 'RotoWire', 'source_phrase': 'ruled out', 'canonical_status': 'OUT', 'parse_type': 'keyword', 'confidence': 0.95},
    {'source': 'RotoWire', 'source_phrase': 'will not play', 'canonical_status': 'OUT', 'parse_type': 'keyword', 'confidence': 0.95},
    {'source': 'RotoWire', 'source_phrase': 'not expected to play', 'canonical_status': 'DOUBTFUL', 'parse_type': 'keyword', 'confidence': 0.85},
    {'source': 'RotoWire', 'source_phrase': 'questionable', 'canonical_status': 'QUESTIONABLE', 'parse_type': 'keyword', 'confidence': 0.85},
    {'source': 'RotoWire', 'source_phrase': 'game-time decision', 'canonical_status': 'GTD', 'parse_type': 'keyword', 'confidence': 0.9},
    {'source': 'RotoWire', 'source_phrase': 'probable', 'canonical_status': 'PROBABLE', 'parse_type': 'keyword', 'confidence': 0.85},
    {'source': 'RotoWire', 'source_phrase': 'available', 'canonical_status': 'ACTIVE', 'parse_type': 'keyword', 'confidence': 0.9},
    {'source': 'RotoWire', 'source_phrase': 'minutes limit', 'canonical_status': 'MINUTES_LIMIT', 'parse_type': 'keyword', 'confidence': 0.9},
    {'source': 'RotoWire', 'source_phrase': 'restriction', 'canonical_status': 'MINUTES_LIMIT', 'parse_type': 'keyword', 'confidence': 0.85},
    {'source': 'RotoWire', 'source_phrase': 'rest', 'canonical_status': 'OUT_REST', 'parse_type': 'keyword', 'confidence': 0.8},
    {'source': 'RotoWire', 'source_phrase': 'load management', 'canonical_status': 'OUT_REST', 'parse_type': 'keyword', 'confidence': 0.9},
    {'source': 'RotoWire', 'source_phrase': 'season-ending', 'canonical_status': 'SEASON_ENDING', 'parse_type': 'keyword', 'confidence': 0.99},
    # RealGM keywords
    {'source': 'RealGM', 'source_phrase': 'out', 'canonical_status': 'OUT', 'parse_type': 'keyword', 'confidence': 0.8},
    {'source': 'RealGM', 'source_phrase': 'expected to miss', 'canonical_status': 'OUT', 'parse_type': 'keyword', 'confidence': 0.85},
    {'source': 'RealGM', 'source_phrase': 'surgery', 'canonical_status': 'OUT', 'parse_type': 'keyword', 'confidence': 0.9},
    {'source': 'RealGM', 'source_phrase': 'returns', 'canonical_status': 'ACTIVE', 'parse_type': 'keyword', 'confidence': 0.85},
    {'source': 'RealGM', 'source_phrase': 'cleared', 'canonical_status': 'ACTIVE', 'parse_type': 'keyword', 'confidence': 0.9},
    {'source': 'RealGM', 'source_phrase': 'underwent', 'canonical_status': 'OUT', 'parse_type': 'keyword', 'confidence': 0.95},
    {'source': 'RealGM', 'source_phrase': 'leaves game', 'canonical_status': 'OUT', 'parse_type': 'keyword', 'confidence': 0.8},
    # Perplexity Semantic signals
    {'source': 'Perplexity', 'source_phrase': 'will play', 'canonical_status': 'ACTIVE', 'parse_type': 'semantic', 'confidence': 0.85},
    {'source': 'Perplexity', 'source_phrase': 'good to go', 'canonical_status': 'ACTIVE', 'parse_type': 'semantic', 'confidence': 0.85},
    {'source': 'Perplexity', 'source_phrase': 'starting tonight', 'canonical_status': 'ACTIVE', 'parse_type': 'semantic', 'confidence': 0.9},
    {'source': 'Perplexity', 'source_phrase': 'sitting out', 'canonical_status': 'OUT', 'parse_type': 'semantic', 'confidence': 0.85},
    {'source': 'Perplexity', 'source_phrase': "won't play", 'canonical_status': 'OUT', 'parse_type': 'semantic', 'confidence': 0.9},
    {'source': 'Perplexity', 'source_phrase': 'coach confirmed', 'canonical_status': 'ACTIVE', 'parse_type': 'semantic', 'confidence': 0.95},
    {'source': 'Perplexity', 'source_phrase': 'no designation', 'canonical_status': 'ACTIVE', 'parse_type': 'semantic', 'confidence': 0.9},
]

SOURCE_CONFIDENCE_DECAY = {
    'ESPN': {'base_confidence': 1.0, 'decay_hours': 12},
    'Tank01': {'base_confidence': 0.9, 'decay_hours': 24},
    'BDL': {'base_confidence': 0.8, 'decay_hours': 24},
    'RotoWire': {'base_confidence': 0.95, 'decay_hours': 6},
    'RealGM': {'base_confidence': 0.85, 'decay_hours': 12},
    'Perplexity': {'base_confidence': 0.85, 'decay_hours': 4},
}

def get_category(status_code):
    """Return the category for a given status code."""
    status_info = INJURY_TAXONOMY.get(status_code.upper())
    if status_info:
        return status_info['category']
    return 'UNCERTAIN'

def semantic_distance(status_a, status_b):
    """Calculate the semantic distance between two status codes."""
    a_info = INJURY_TAXONOMY.get(status_a.upper())
    b_info = INJURY_TAXONOMY.get(status_b.upper())
    
    if a_info and b_info:
        return abs(a_info['severity_score'] - b_info['severity_score'])
    
    return 0
