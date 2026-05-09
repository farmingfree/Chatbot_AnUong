# Production Readiness Action Plan

**Date:** 2026-05-09  
**Current Status:** CONDITIONAL PASS (6.5/10)  
**Target:** PRODUCTION READY (9.0/10)  

---

## Critical Issues (Must Fix Before Production)

### 🔴 Issue 1: Review Content Extraction (33% null, 33% duplicate, 42% truncated)

**Root Cause:**
- CSS selectors not matching current Google Maps DOM structure
- "More" button not being clicked to expand truncated reviews
- Insufficient wait time after clicking "More"
- Review panel not scrolled to load all reviews

**Fix Applied:**
- ✅ Added multiple fallback content selectors
- ✅ Added "More" button click logic with wait
- ✅ Added review panel scrolling (2 iterations)
- ✅ Added content length validation (>5 chars)
- ⏳ Testing in progress (test_single_place.py)

**Verification Needed:**
1. Run full crawl with 20+ places
2. Check null content rate < 10%
3. Check duplicate rate < 5%
4. Check truncation rate < 10%
5. Manually verify 10 random reviews match Google Maps

**Files Modified:**
- `run_live_crawl.py` lines 153-210

---

### 🔴 Issue 2: Google Place ID Extraction (0% coverage)

**Root Cause:**
- Regex pattern too narrow, only matching `ChIJ[\w-]+` format
- Google Maps URLs use multiple place_id formats
- Some URLs don't contain place_id at all (use CID instead)

**Fix Applied:**
- ✅ Added 3 fallback patterns for place_id extraction
- ✅ Pattern 1: `place/[^/]+/(ChIJ[\w-]+)` (path format)
- ✅ Pattern 2: `(ChIJ[\w-]+)` (anywhere in URL)
- ✅ Pattern 3: `ftid=(0x[0-9a-f]+:0x[0-9a-f]+)` (ftid parameter)
- ⏳ Testing in progress

**Verification Needed:**
1. Run full crawl with 20+ places
2. Check place_id coverage > 80%
3. For places without place_id, verify google_cid is present
4. Manually verify 5 random place_ids are correct

**Files Modified:**
- `run_live_crawl.py` lines 37-51

---

## Medium Priority Issues (Should Fix)

### 🟡 Issue 3: Phone Number Extraction (50% coverage)

**Root Cause:**
- Some places don't display phone publicly
- CSS selector may have changed
- Phone button may be hidden or require interaction

**Recommended Fix:**
1. Add multiple fallback selectors for phone extraction
2. Try clicking phone button if present
3. Check for phone in structured data (JSON-LD)
4. Accept that some places legitimately don't have phones

**Files to Modify:**
- `run_live_crawl.py` lines 133-140

---

### 🟡 Issue 4: Anti-Bot Stability (Not Tested)

**Status:** User requested 50+ sequential crawls, not yet performed

**Recommended Test:**
```python
# test_anti_bot.py
for i in range(50):
    result = await crawl_one_query(page, "pho district 1", limit=1)
    if not result:
        print(f"BLOCKED at iteration {i}")
        break
    await asyncio.sleep(random.uniform(3, 7))  # random delay
```

**Success Criteria:**
- Complete 50 crawls without CAPTCHA
- Complete 50 crawls without rate limiting
- Complete 50 crawls without IP ban

---

### 🟡 Issue 5: Parser Robustness (Not Tested)

**Status:** Need to identify fragile CSS selectors

**Recommended Test:**
1. Run crawler on 100+ places
2. Log which selectors fail most often
3. Identify selectors that break when Google updates UI
4. Replace fragile selectors with JSON-LD or data attributes

**Fragile Selectors to Review:**
- `div.d4r55` (review author)
- `span.wiI7pd` (review content)
- `div.fontDisplayLarge` (rating)
- `button[data-item-id="address"]` (address)

**Robust Alternatives:**
- JSON-LD structured data (`<script type="application/ld+json">`)
- Data attributes (`data-review-id`, `data-place-id`)
- ARIA labels (`aria-label`)

---

## Low Priority Issues (Nice to Have)

### 🟢 Issue 6: Performance Benchmarking

**Status:** Not measured

**Recommended Metrics:**
- Average time per place (currently ~12s)
- Memory usage per place
- Network bandwidth usage
- Database insert time

**Target Performance:**
- < 10s per place
- < 500MB RAM for 100 places
- < 100 DB queries per place

---

### 🟢 Issue 7: Error Recovery

**Current Behavior:** Silent failures, continues to next place

**Recommended Improvements:**
1. Retry failed places (max 3 attempts)
2. Save failed place URLs to retry queue
3. Log detailed error context (screenshot, HTML, stack trace)
4. Alert on high failure rate (>20%)

---

## Testing Checklist

### Phase 1: Unit Tests (Fixes Verification)
- [x] Test place_id extraction with multiple URL formats
- [⏳] Test review extraction with real Google Maps page
- [ ] Test phone extraction with multiple selectors
- [ ] Test coordinate extraction accuracy

### Phase 2: Integration Tests (Small Scale)
- [ ] Crawl 5 places, verify all fields extracted
- [ ] Check review quality (null, duplicate, truncation rates)
- [ ] Check place_id coverage
- [ ] Check database consistency

### Phase 3: Validation Tests (Medium Scale)
- [ ] Crawl 20+ places across 4 queries
- [ ] Run full validation audit (run_validation_audit.py)
- [ ] Generate validation report
- [ ] Verify production readiness score > 8.0/10

### Phase 4: Stress Tests (Large Scale)
- [ ] Anti-bot stability: 50+ sequential crawls
- [ ] Parser robustness: 100+ places
- [ ] Performance benchmarking
- [ ] Error recovery testing

---

## Production Deployment Criteria

**Must Have (Blocking):**
- ✅ Coordinate accuracy > 95%
- ⏳ Review null content < 10%
- ⏳ Review duplicates < 5%
- ⏳ Review truncation < 10%
- ⏳ Place ID coverage > 80%
- ✅ Database consistency 100%
- ✅ Entity matching accuracy 100%

**Should Have (Non-Blocking):**
- Phone coverage > 70%
- Anti-bot stability: 50 crawls without block
- Parser robustness: < 5% selector failures
- Performance: < 10s per place

**Nice to Have:**
- Error recovery with retry logic
- Performance monitoring dashboard
- Automated quality alerts
- A/B testing framework

---

## Timeline Estimate

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| **Phase 1** | Verify fixes (place_id, reviews) | 1-2 hours |
| **Phase 2** | Small scale integration test | 1 hour |
| **Phase 3** | Medium scale validation | 2-3 hours |
| **Phase 4** | Stress testing | 3-4 hours |
| **Phase 5** | Fix remaining issues | 2-4 hours |
| **Phase 6** | Final validation | 1 hour |
| **Total** | | **10-15 hours** |

---

## Current Status Summary

**Completed:**
- ✅ V2 crawler architecture with 8 modules
- ✅ Multi-signal coordinate extraction
- ✅ Geographic validation (HCM bounds, district consistency)
- ✅ Entity validation (fuzzy matching, chain detection)
- ✅ Debug artifacts system
- ✅ Quality metrics framework
- ✅ Database schema migration
- ✅ Initial validation audit (26 places, 24 reviews)
- ✅ Identified critical issues
- ✅ Applied fixes for place_id and review extraction

**In Progress:**
- ⏳ Testing place_id extraction fixes
- ⏳ Testing review extraction fixes

**Pending:**
- ⏸️ Phone extraction improvements
- ⏸️ Anti-bot stability testing
- ⏸️ Parser robustness testing
- ⏸️ Performance benchmarking
- ⏸️ Full validation with 20+ places
- ⏸️ Final production readiness report

---

## Next Immediate Steps

1. **Wait for test_single_place.py to complete** (currently running)
2. **Verify fixes work:**
   - Check if place_id is extracted
   - Check if reviews have content (not null)
   - Check if reviews are not truncated
3. **Run full crawl with fixes:**
   - Use run_live_crawl.py with 4 queries
   - Target 20+ places, 50+ reviews
4. **Run validation audit:**
   - Use run_validation_audit.py
   - Generate new validation report
5. **Compare before/after metrics:**
   - Review null content: 33% → target < 10%
   - Review duplicates: 33% → target < 5%
   - Review truncation: 42% → target < 10%
   - Place ID coverage: 0% → target > 80%
6. **If metrics meet targets:**
   - Proceed to stress testing (anti-bot, parser robustness)
7. **If metrics don't meet targets:**
   - Debug and iterate on fixes
   - Repeat testing cycle

---

## Risk Assessment

**High Risk:**
- Google Maps UI changes breaking selectors (mitigation: use JSON-LD, data attributes)
- Anti-bot detection blocking crawler (mitigation: stealth mode, delays, proxies)
- Review extraction still failing after fixes (mitigation: more fallback selectors)

**Medium Risk:**
- Performance degradation with large datasets (mitigation: batch processing, caching)
- Database connection pool exhaustion (mitigation: connection limits, timeouts)
- Memory leaks in long-running crawls (mitigation: browser restart every N places)

**Low Risk:**
- Phone extraction remaining at 50% (acceptable if places don't have phones)
- Place ID extraction < 80% (acceptable if google_cid is present)
- Minor coordinate drift < 100m (acceptable for most use cases)

---

## Success Metrics

**Production Ready = 9.0/10 Score:**
- Coordinate accuracy: 95%+ ✅ (currently 100%)
- Review quality: 90%+ ⏳ (currently 67%)
- Place ID coverage: 80%+ ⏳ (currently 0%)
- Database consistency: 100% ✅ (currently 100%)
- Entity matching: 95%+ ✅ (currently 100%)
- Anti-bot stability: 50 crawls ⏸️ (not tested)
- Parser robustness: 95%+ ⏸️ (not tested)

**Current Score: 6.5/10**
**Target Score: 9.0/10**
**Gap: 2.5 points**

**To close the gap:**
- Fix review extraction: +1.5 points
- Fix place_id extraction: +0.5 points
- Pass anti-bot testing: +0.3 points
- Pass parser robustness: +0.2 points
