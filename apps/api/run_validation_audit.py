"""
Full end-to-end validation of Google Maps crawler output.

Runs all validation checks and produces a comprehensive report
with evidence files.
"""
import asyncio
import json
import re
import math
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Any, Tuple, Optional

from sqlalchemy import text
from app.database import AsyncSessionLocal

REPORT_DIR = Path(r"C:\Users\admin\Documents\chatbot_anuong\apps\api\data\validation_reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

HCM_BOUNDS = {'lat_min': 10.35, 'lat_max': 11.20, 'lng_min': 106.35, 'lng_max': 107.05}
DISTRICT_CENTROIDS = {
    'Quận 1': (10.7756, 106.7019), 'Quận 2': (10.7897, 106.7472),
    'Quận 3': (10.7847, 106.6878), 'Quận 4': (10.7575, 106.7025),
    'Quận 5': (10.7553, 106.6672), 'Quận 6': (10.7478, 106.6347),
    'Quận 7': (10.7333, 106.7219), 'Quận 8': (10.7389, 106.6289),
    'Quận 10': (10.7731, 106.6697), 'Quận 11': (10.7628, 106.6503),
    'Quận 12': (10.8631, 106.6700), 'Binh Thanh': (10.8142, 106.7108),
}


def haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


async def run_full_validation():
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {},
        'summary': {}
    }

    async with AsyncSessionLocal() as db:

        # ================================================================
        # CHECK 1: DATA INVENTORY
        # ================================================================
        print("\n=== CHECK 1: DATA INVENTORY ===")

        totals = (await db.execute(text("""
            SELECT
                COUNT(*) as total_places,
                COUNT(*) FILTER (WHERE source_data->>'source' IN ('google_maps_playwright_e2e','google_maps_v2')) as live_places,
                COUNT(*) FILTER (WHERE lat IS NOT NULL) as has_coords,
                COUNT(*) FILTER (WHERE address IS NOT NULL AND address != '') as has_address,
                COUNT(*) FILTER (WHERE rating_google IS NOT NULL) as has_rating,
                COUNT(*) FILTER (WHERE google_place_id IS NOT NULL) as has_place_id
            FROM places
        """))).mappings().first()

        review_totals = (await db.execute(text("""
            SELECT
                COUNT(*) as total_reviews,
                COUNT(*) FILTER (WHERE content IS NOT NULL AND LENGTH(content) > 10) as has_content,
                COUNT(*) FILTER (WHERE rating IS NOT NULL) as has_rating,
                COUNT(*) FILTER (WHERE author_name IS NOT NULL) as has_author
            FROM reviews
        """))).scalar_one()

        print(f"  Places: {totals['total_places']} total, {totals['live_places']} from live crawl")
        print(f"  Coords: {totals['has_coords']}/{totals['total_places']}")
        print(f"  Reviews total: {review_totals}")

        report['checks']['inventory'] = {
            'places': dict(totals),
            'reviews': int(review_totals)
        }

        # ================================================================
        # CHECK 2: COORDINATE ACCURACY DEEP DIVE
        # ================================================================
        print("\n=== CHECK 2: COORDINATE ACCURACY ===")

        places_with_coords = (await db.execute(text("""
            SELECT id::text, name, address, lat, lng, district,
                   ST_AsText(geom) as geom_text,
                   source_data
            FROM places
            WHERE lat IS NOT NULL AND lng IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 20
        """))).mappings().all()

        coord_issues = []
        coord_ok = []

        for p in places_with_coords:
            issues = []
            lat, lng = p['lat'], p['lng']

            # HCM bounds
            in_hcm = (HCM_BOUNDS['lat_min'] <= lat <= HCM_BOUNDS['lat_max'] and
                      HCM_BOUNDS['lng_min'] <= lng <= HCM_BOUNDS['lng_max'])
            if not in_hcm:
                issues.append(f"OUTSIDE_HCM: ({lat:.4f},{lng:.4f})")

            # Null island
            if abs(lat) < 0.01 and abs(lng) < 0.01:
                issues.append("NULL_ISLAND")

            # Geometry consistency (geom should match lat/lng)
            geom = p['geom_text']
            if geom:
                # POINT(lng lat) format
                m = re.search(r'POINT\((-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)', geom)
                if m:
                    geom_lng, geom_lat = float(m.group(1)), float(m.group(2))
                    lat_diff = abs(lat - geom_lat)
                    lng_diff = abs(lng - geom_lng)
                    if lat_diff > 0.0001 or lng_diff > 0.0001:
                        issues.append(f"GEOM_MISMATCH: lat_diff={lat_diff:.6f} lng_diff={lng_diff:.6f}")

            # District distance
            district = p['district']
            if district and district in DISTRICT_CENTROIDS:
                clat, clng = DISTRICT_CENTROIDS[district]
                dist_km = haversine_km(lat, lng, clat, clng)
                if dist_km > 8:
                    issues.append(f"FAR_FROM_DISTRICT: {dist_km:.1f}km from {district}")

            entry = {
                'name': p['name'],
                'lat': lat,
                'lng': lng,
                'district': district,
                'issues': issues
            }
            if issues:
                coord_issues.append(entry)
                print(f"  ISSUE {p['name']}: {', '.join(issues)}")
            else:
                coord_ok.append(entry)

        coord_score = len(coord_ok) / max(len(places_with_coords), 1)
        print(f"  Coord OK: {len(coord_ok)}/{len(places_with_coords)} = {coord_score:.1%}")

        report['checks']['coordinate_accuracy'] = {
            'places_checked': len(places_with_coords),
            'coord_ok': len(coord_ok),
            'coord_issues': len(coord_issues),
            'score': round(coord_score, 3),
            'passed': coord_score >= 0.9,
            'issue_details': coord_issues,
            'ok_details': coord_ok
        }

        # Save coordinate evidence
        (REPORT_DIR / "coord_evidence.json").write_text(
            json.dumps({'ok': coord_ok, 'issues': coord_issues}, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

        # ================================================================
        # CHECK 3: DATA AUTHENTICITY
        # ================================================================
        print("\n=== CHECK 3: DATA AUTHENTICITY ===")

        sample_places = (await db.execute(text("""
            SELECT id::text, name, address, lat, lng, rating_google, review_count,
                   phone, google_place_id, source_data
            FROM places
            ORDER BY created_at DESC
            LIMIT 20
        """))).mappings().all()

        authenticity_checks = []
        fake_count = 0
        real_count = 0

        for p in sample_places:
            flags = []
            name = p['name'] or ''
            address = p['address'] or ''
            rating = p['rating_google']
            reviews = p['review_count']

            # Fake data patterns
            if re.search(r'#\d{3,}', name):
                flags.append('FAKE_NAME_PATTERN')
            if 'ChIJstatic' in str(p.get('google_place_id') or ''):
                flags.append('STATIC_PLACE_ID')
            if re.search(r'(Fake|Test|Sample|Demo)', name, re.IGNORECASE):
                flags.append('TEST_DATA_KEYWORD')

            # Quality checks
            if not address or len(address) < 15:
                flags.append('MISSING_OR_SHORT_ADDRESS')
            if rating and not (1.0 <= rating <= 5.0):
                flags.append(f'INVALID_RATING:{rating}')
            if reviews is not None and reviews < 0:
                flags.append('NEGATIVE_REVIEW_COUNT')

            # Real data indicators
            has_realistic_rating = rating and 2.5 <= rating <= 5.0
            has_real_address = bool(re.search(r'\d+', address))
            has_vn_chars = bool(re.search(r'[àáâãèéêìíòóôõùúýăđơư]', name + address, re.IGNORECASE))

            is_real = has_realistic_rating and has_real_address and not flags
            if is_real:
                real_count += 1
            elif flags:
                fake_count += 1

            authenticity_checks.append({
                'name': name,
                'address': address[:60] if address else None,
                'rating': rating,
                'reviews': reviews,
                'flags': flags,
                'is_real': is_real,
                'has_vn_chars': has_vn_chars
            })

        auth_score = real_count / max(len(sample_places), 1)
        print(f"  Real: {real_count}/{len(sample_places)} = {auth_score:.1%}")
        print(f"  Fake/suspicious: {fake_count}")
        if fake_count:
            for ch in authenticity_checks:
                if ch['flags']:
                    print(f"  FLAGGED: {ch['name']} => {ch['flags']}")

        report['checks']['data_authenticity'] = {
            'places_checked': len(sample_places),
            'real_count': real_count,
            'fake_count': fake_count,
            'score': round(auth_score, 3),
            'passed': fake_count == 0 and auth_score >= 0.8,
            'sample': authenticity_checks
        }

        # ================================================================
        # CHECK 4: REVIEW EXTRACTION QUALITY
        # ================================================================
        print("\n=== CHECK 4: REVIEW EXTRACTION ===")

        reviews_sample = (await db.execute(text("""
            SELECT r.id::text, r.author_name, r.rating, r.content, r.source,
                   p.name as place_name, p.id::text as place_id
            FROM reviews r
            JOIN places p ON r.place_id = p.id
            LIMIT 50
        """))).mappings().all()

        review_checks = []
        dup_content = Counter()
        null_content = 0
        null_author = 0
        invalid_rating = 0
        truncated = 0

        content_to_places = defaultdict(set)

        for r in reviews_sample:
            content = r['content'] or ''
            author = r['author_name'] or ''

            if content:
                dup_content[content[:100]] += 1
                content_to_places[content[:100]].add(r['place_id'])

            if not content or len(content) < 5:
                null_content += 1
            if not author:
                null_author += 1
            if r['rating'] is not None and not (1 <= r['rating'] <= 5):
                invalid_rating += 1
            if content.endswith(('…', '...')):
                truncated += 1

        # Duplication check
        dup_contents = {k: v for k, v in dup_content.items() if v > 1}
        cross_place_contamination = {k for k, places in content_to_places.items() if len(places) > 1}

        print(f"  Reviews sampled: {len(reviews_sample)}")
        print(f"  Null content: {null_content}")
        print(f"  Null author: {null_author}")
        print(f"  Duplicated content: {len(dup_contents)}")
        print(f"  Cross-place contamination: {len(cross_place_contamination)}")
        print(f"  Truncated: {truncated}")
        print(f"  Invalid rating: {invalid_rating}")

        review_failures = []
        if null_content > len(reviews_sample) * 0.3:
            review_failures.append(f"HIGH_NULL_CONTENT: {null_content}/{len(reviews_sample)}")
        if cross_place_contamination:
            review_failures.append(f"CROSS_CONTAMINATION: {len(cross_place_contamination)} contents appear in multiple places")

        review_score = 1.0
        review_score -= 0.3 * (null_content / max(len(reviews_sample), 1))
        review_score -= 0.5 * (len(cross_place_contamination) / max(len(reviews_sample), 1))
        review_score -= 0.3 * (len(dup_contents) / max(len(reviews_sample), 1))
        review_score = max(0, review_score)

        report['checks']['review_extraction'] = {
            'reviews_checked': len(reviews_sample),
            'null_content': null_content,
            'null_author': null_author,
            'duplicated_content': len(dup_contents),
            'cross_place_contamination': len(cross_place_contamination),
            'truncated': truncated,
            'invalid_rating': invalid_rating,
            'score': round(review_score, 3),
            'passed': review_score >= 0.7 and not cross_place_contamination,
            'failures': review_failures,
            'sample': [dict(r) for r in reviews_sample[:10]]
        }

        # ================================================================
        # CHECK 5: DATABASE CONSISTENCY
        # ================================================================
        print("\n=== CHECK 5: DATABASE CONSISTENCY ===")

        db_issues = []

        # Duplicate place_ids
        dup_pids = (await db.execute(text("""
            SELECT google_place_id, COUNT(*) as cnt
            FROM places WHERE google_place_id IS NOT NULL
            GROUP BY google_place_id HAVING COUNT(*) > 1
        """))).mappings().all()
        if dup_pids:
            db_issues.append(f"DUP_PLACE_IDS: {len(dup_pids)} duplicates")
            for d in dup_pids:
                print(f"  DUP place_id: {d['google_place_id']} x{d['cnt']}")

        # Duplicate place names + addresses
        dup_names = (await db.execute(text("""
            SELECT name, address, COUNT(*) as cnt
            FROM places
            GROUP BY name, address
            HAVING COUNT(*) > 1
        """))).mappings().all()
        if dup_names:
            db_issues.append(f"DUP_NAME_ADDRESS: {len(dup_names)} duplicates")
            for d in dup_names:
                print(f"  DUP name+addr: '{d['name']}' @ {d['address']} x{d['cnt']}")

        # Geometry consistency check
        bad_geom = (await db.execute(text("""
            SELECT COUNT(*) FROM places
            WHERE lat IS NOT NULL AND lng IS NOT NULL
              AND geom IS NOT NULL
              AND ABS(ST_Y(geom) - lat) > 0.001
        """))).scalar()
        if bad_geom:
            db_issues.append(f"BAD_GEOM: {bad_geom} geometry-lat mismatches")
            print(f"  WARN: {bad_geom} geom/lat mismatches")

        # Missing coords with district set
        missing_coords = (await db.execute(text("""
            SELECT COUNT(*) FROM places WHERE lat IS NULL OR lng IS NULL
        """))).scalar()
        if missing_coords > 0:
            db_issues.append(f"MISSING_COORDS: {missing_coords} places")
            print(f"  WARN: {missing_coords} places with no coordinates")

        # Orphaned reviews
        orphaned = (await db.execute(text("""
            SELECT COUNT(*) FROM reviews r
            LEFT JOIN places p ON r.place_id = p.id
            WHERE p.id IS NULL
        """))).scalar()
        if orphaned > 0:
            db_issues.append(f"ORPHANED_REVIEWS: {orphaned}")

        # Name normalization consistency
        unnorm = (await db.execute(text("""
            SELECT COUNT(*) FROM places
            WHERE name IS NOT NULL AND name != ''
              AND (name_normalized IS NULL OR name_normalized = '')
        """))).scalar()
        if unnorm > 0:
            db_issues.append(f"UNNORMALIZED_NAMES: {unnorm}")

        print(f"  Issues found: {len(db_issues)}")
        for issue in db_issues:
            print(f"  - {issue}")

        db_score = max(0, 1.0 - len(db_issues) * 0.1)
        report['checks']['database_consistency'] = {
            'issues': db_issues,
            'dup_place_ids': len(dup_pids),
            'dup_names_addresses': len(dup_names),
            'bad_geometry': int(bad_geom),
            'missing_coords': int(missing_coords),
            'orphaned_reviews': int(orphaned),
            'unnormalized_names': int(unnorm),
            'score': round(db_score, 3),
            'passed': len(db_issues) == 0
        }

        # ================================================================
        # CHECK 6: ENTITY MATCHING QUALITY
        # ================================================================
        print("\n=== CHECK 6: ENTITY MATCHING ===")

        # Check review counts are realistic
        unrealistic = (await db.execute(text("""
            SELECT name, review_count FROM places
            WHERE review_count > 1000000 OR review_count < 0
        """))).mappings().all()

        # Check rating range
        bad_ratings = (await db.execute(text("""
            SELECT name, rating_google FROM places
            WHERE rating_google IS NOT NULL
              AND (rating_google < 1.0 OR rating_google > 5.0)
        """))).mappings().all()

        # Check for suspicious names
        suspicious_names = (await db.execute(text("""
            SELECT name FROM places
            WHERE name ~ '[#@]{2,}'
               OR name ~ '\d{5,}'
               OR LENGTH(name) < 3
        """))).mappings().all()

        entity_issues = []
        if unrealistic:
            entity_issues.append(f"UNREALISTIC_REVIEW_COUNT: {len(unrealistic)}")
        if bad_ratings:
            entity_issues.append(f"BAD_RATINGS: {[r['name'] for r in bad_ratings]}")
        if suspicious_names:
            entity_issues.append(f"SUSPICIOUS_NAMES: {[n['name'] for n in suspicious_names]}")

        print(f"  Unrealistic review counts: {len(unrealistic)}")
        print(f"  Bad ratings: {len(bad_ratings)}")
        print(f"  Suspicious names: {len(suspicious_names)}")

        report['checks']['entity_matching'] = {
            'issues': entity_issues,
            'unrealistic_reviews': [dict(r) for r in unrealistic],
            'bad_ratings': [dict(r) for r in bad_ratings],
            'suspicious_names': [dict(n) for n in suspicious_names],
            'score': max(0, 1.0 - len(entity_issues) * 0.15),
            'passed': len(entity_issues) == 0
        }

        # ================================================================
        # CHECK 7: PARSER ROBUSTNESS - FIELD COMPLETENESS
        # ================================================================
        print("\n=== CHECK 7: PARSER COMPLETENESS ===")

        completeness = (await db.execute(text("""
            SELECT
                COUNT(*) as total,
                ROUND(100.0 * COUNT(*) FILTER (WHERE name IS NOT NULL AND name != '') / COUNT(*), 1) as pct_name,
                ROUND(100.0 * COUNT(*) FILTER (WHERE address IS NOT NULL AND address != '') / COUNT(*), 1) as pct_address,
                ROUND(100.0 * COUNT(*) FILTER (WHERE lat IS NOT NULL AND lng IS NOT NULL) / COUNT(*), 1) as pct_coords,
                ROUND(100.0 * COUNT(*) FILTER (WHERE rating_google IS NOT NULL) / COUNT(*), 1) as pct_rating,
                ROUND(100.0 * COUNT(*) FILTER (WHERE review_count IS NOT NULL AND review_count > 0) / COUNT(*), 1) as pct_reviews,
                ROUND(100.0 * COUNT(*) FILTER (WHERE phone IS NOT NULL) / COUNT(*), 1) as pct_phone,
                ROUND(100.0 * COUNT(*) FILTER (WHERE google_place_id IS NOT NULL) / COUNT(*), 1) as pct_place_id,
                ROUND(100.0 * COUNT(*) FILTER (WHERE image_urls IS NOT NULL AND image_urls::text != '[]') / COUNT(*), 1) as pct_images
            FROM places
            WHERE source_data->>'source' IN ('google_maps_playwright_e2e', 'google_maps_v2')
        """))).mappings().first()

        print(f"  Total real-crawled places: {completeness['total']}")
        print(f"  Name: {completeness['pct_name']}%")
        print(f"  Address: {completeness['pct_address']}%")
        print(f"  Coords: {completeness['pct_coords']}%")
        print(f"  Rating: {completeness['pct_rating']}%")
        print(f"  Reviews: {completeness['pct_reviews']}%")
        print(f"  Phone: {completeness['pct_phone']}%")
        print(f"  Place ID: {completeness['pct_place_id']}%")
        print(f"  Images: {completeness['pct_images']}%")

        completeness_dict = dict(completeness)
        critical_fields = ['pct_name', 'pct_address', 'pct_coords', 'pct_rating']
        avg_critical = sum(float(completeness_dict.get(f) or 0) for f in critical_fields) / len(critical_fields)

        low_completeness = [f for f in critical_fields if float(completeness_dict.get(f) or 0) < 80]

        report['checks']['parser_completeness'] = {
            'completeness': {k: float(v) if v is not None else 0 for k, v in completeness_dict.items()},
            'avg_critical_completeness': round(avg_critical / 100, 3),
            'low_completeness_fields': low_completeness,
            'score': round(avg_critical / 100, 3),
            'passed': len(low_completeness) == 0
        }

        # ================================================================
        # CHECK 8: SPECIFIC KNOWN PLACES VALIDATION
        # ================================================================
        print("\n=== CHECK 8: SPECIFIC PLACES CROSS-CHECK ===")

        # Pho Hung should be at ~10.7648891, 106.6877054
        # Pho Viet Nam should be at ~10.771386, 106.6961339
        known_places = {
            'Pho Hung': {'expected_lat': 10.7648891, 'expected_lng': 106.6877054,
                         'expected_rating_min': 4.0, 'expected_address_contains': 'Nguyễn Trãi'},
            'Phở Việt Nam': {'expected_lat': 10.771386, 'expected_lng': 106.6961339,
                             'expected_rating_min': 4.0, 'expected_address_contains': 'Phạm Hồng Thái'},
        }

        place_cross_checks = []
        for name, expected in known_places.items():
            place = (await db.execute(text("""
                SELECT name, address, lat, lng, rating_google, review_count, google_place_id
                FROM places
                WHERE name ILIKE :name
                LIMIT 1
            """), {'name': f'%{name}%'})).mappings().first()

            if not place:
                place_cross_checks.append({
                    'name': name,
                    'found': False,
                    'issues': ['NOT_IN_DATABASE']
                })
                print(f"  NOT FOUND: {name}")
                continue

            issues = []
            # Check coordinate accuracy (within 200m)
            if place['lat'] and place['lng']:
                dist_m = haversine_km(place['lat'], place['lng'],
                                      expected['expected_lat'], expected['expected_lng']) * 1000
                if dist_m > 200:
                    issues.append(f"COORD_DRIFT: {dist_m:.0f}m from expected")
                print(f"  {name}: coords ({place['lat']:.6f},{place['lng']:.6f}) "
                      f"vs expected ({expected['expected_lat']},{expected['expected_lng']}) "
                      f"=> {dist_m:.0f}m drift")
            else:
                issues.append("MISSING_COORDS")

            # Check rating
            if place['rating_google'] and place['rating_google'] < expected['expected_rating_min']:
                issues.append(f"LOW_RATING: {place['rating_google']} < {expected['expected_rating_min']}")

            # Check address
            if not (expected['expected_address_contains'] in (place['address'] or '')):
                issues.append(f"ADDRESS_MISMATCH: expected '{expected['expected_address_contains']}'")

            place_cross_checks.append({
                'name': name,
                'found': True,
                'actual': {
                    'address': place['address'],
                    'lat': place['lat'],
                    'lng': place['lng'],
                    'rating': place['rating_google']
                },
                'expected': expected,
                'issues': issues,
                'passed': len(issues) == 0
            })

        cross_check_score = sum(1 for c in place_cross_checks if c.get('passed', False)) / max(len(known_places), 1)
        report['checks']['known_places_cross_check'] = {
            'checks': place_cross_checks,
            'score': round(cross_check_score, 3),
            'passed': cross_check_score >= 0.5
        }

        # ================================================================
        # SQL DIAGNOSTICS DUMP
        # ================================================================
        print("\n=== SQL DIAGNOSTICS ===")

        diag_rows = (await db.execute(text("""
            SELECT
                p.id::text,
                p.name,
                ROUND(p.lat::numeric, 6)::text as lat,
                ROUND(p.lng::numeric, 6)::text as lng,
                p.address,
                p.rating_google,
                p.review_count,
                p.district,
                p.google_place_id,
                p.validation_status,
                p.source_data->>'source' as source,
                COUNT(r.id) as db_review_count
            FROM places p
            LEFT JOIN reviews r ON r.place_id = p.id
            GROUP BY p.id, p.name, p.lat, p.lng, p.address,
                     p.rating_google, p.review_count, p.district,
                     p.google_place_id, p.validation_status, p.source_data
            ORDER BY p.created_at DESC
            LIMIT 30
        """))).mappings().all()

        sql_output = [dict(r) for r in diag_rows]
        (REPORT_DIR / "sql_diagnostics.json").write_text(
            json.dumps(sql_output, ensure_ascii=False, indent=2, default=str),
            encoding='utf-8'
        )
        print(f"  Diagnostic rows: {len(sql_output)} saved to sql_diagnostics.json")

    # ================================================================
    # GENERATE FINAL SUMMARY
    # ================================================================
    all_scores = [
        report['checks'][k]['score']
        for k in report['checks']
        if 'score' in report['checks'][k]
    ]
    overall_score = sum(all_scores) / max(len(all_scores), 1)

    all_passed = [
        report['checks'][k].get('passed', False)
        for k in report['checks']
    ]
    pass_count = sum(all_passed)

    failures_per_check = {}
    for k, v in report['checks'].items():
        if not v.get('passed', True):
            failures_per_check[k] = v.get('failures', v.get('issues', []))

    production_ready = overall_score >= 0.8 and pass_count >= len(all_passed) * 0.7

    report['summary'] = {
        'overall_score': round(overall_score, 3),
        'checks_passed': pass_count,
        'checks_total': len(all_passed),
        'production_ready': production_ready,
        'key_failures': failures_per_check,
        'recommendation': (
            "READY" if production_ready else
            "NEEDS_FIXES" if overall_score >= 0.6 else
            "NOT_READY"
        )
    }

    # Save full report
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    report_path = REPORT_DIR / f"validation_report_{ts}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding='utf-8'
    )

    print("\n" + "="*70)
    print("FINAL VALIDATION REPORT")
    print("="*70)
    print(f"Overall Score:     {overall_score:.1%}")
    print(f"Checks Passed:     {pass_count}/{len(all_passed)}")
    print(f"Production Ready:  {'YES' if production_ready else 'NO'}")
    print(f"Recommendation:    {report['summary']['recommendation']}")
    print(f"\nReport saved to:   {report_path}")
    print(f"SQL diagnostics:   {REPORT_DIR/'sql_diagnostics.json'}")

    print("\nCheck Scores:")
    for k, v in report['checks'].items():
        status = "PASS" if v.get('passed', False) else "FAIL"
        score = v.get('score', 0)
        print(f"  [{status}] {k}: {score:.1%}")

    if failures_per_check:
        print("\nFailed Checks:")
        for check, failures in failures_per_check.items():
            print(f"  {check}:")
            for f in (failures or [])[:3]:
                print(f"    - {f}")

    return report

if __name__ == "__main__":
    asyncio.run(run_full_validation())
