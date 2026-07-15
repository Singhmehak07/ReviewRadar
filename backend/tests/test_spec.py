"""
Comprehensive specification-required tests.
Run from backend/ directory:
    pytest tests/test_spec.py -v
"""
import sys
import os
import json
import pytest
from fastapi.testclient import TestClient

# Add parent directory to path so that backend files can be imported properly
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from predict import predict_review, assign_risk_band, analyze_review, EmptyCleanedTextError, get_risk_interpretation
from signals.consistency import consistency_flag
from text_cleaning import clean_review_text
from main import app, normalize_for_duplicate

client = TestClient(app)


# ── 1. Text Cleaner Tests ───────────────────────────────────────────────────

def test_cleaner_html_decoding_and_tag_removal():
    raw = "<p>This is &amp; feels like a <b>great</b> product!</p>"
    res = clean_review_text(raw)
    assert res["cleaned_text"] == "This is & feels like a great product!"

def test_cleaner_removes_exact_ui_noise_lines():
    raw = (
        "5 ★\n"
        "Wonderful product\n"
        "Certified Buyer, New Delhi\n"
        "15 Jun, 2026\n"
        "The stand feels stable and supports my laptop well.\n"
        "Read More\n"
        "Helpful? 43\n"
        "Permalink\n"
        "Report Abuse"
    )
    res = clean_review_text(raw)
    assert "Wonderful product. The stand feels stable and supports my laptop well." in res["cleaned_text"]
    assert "Read More" not in res["cleaned_text"]
    assert "Helpful? 43" not in res["cleaned_text"]
    assert "Permalink" not in res["cleaned_text"]
    assert "Report Abuse" not in res["cleaned_text"]
    assert res["extracted_rating"] == 5
    assert len(res["removed_noise_lines"]) > 0

def test_cleaner_preserves_helpful_in_genuine_sentence():
    raw = "This stand has been very helpful for work. I highly recommend it."
    res = clean_review_text(raw)
    assert res["cleaned_text"] == "This stand has been very helpful for work. I highly recommend it."
    assert len(res["removed_noise_lines"]) == 0

def test_cleaner_handles_empty_and_whitespace_input():
    assert clean_review_text("")["cleaned_text"] == ""
    assert clean_review_text("   \n\t   ")["cleaned_text"] == ""
    assert clean_review_text(None)["cleaned_text"] == ""


# ── 2. Single-Review Analysis Tests ─────────────────────────────────────────

def test_single_review_shape_and_types():
    res = analyze_review("Absolutely wonderful and outstanding purchase!")
    assert isinstance(res, dict)
    assert "cleaned_text" in res
    assert "risk_score" in res
    assert "risk_band" in res
    assert "risk_label" in res
    assert "interpretation" in res
    assert "reasons" in res
    assert "cleaning" in res
    assert "disclaimer" in res
    assert isinstance(res["risk_score"], float)
    assert isinstance(res["reasons"], list)
    assert len(res["reasons"]) <= 3
    assert res["risk_label"] == "Computer-generated writing risk"
    assert "headline" in res["interpretation"]
    assert "description" in res["interpretation"]
    assert res["disclaimer"] == "Highlights suspicious review patterns; does not prove fraud."

def test_single_review_reasons_contain_no_fraud_claims():
    res = analyze_review("Outstanding quality, highly recommend, best product ever.")
    for reason in res["reasons"]:
        assert "fake" not in reason.lower()
        assert "fraud" not in reason.lower()
        assert "lying" not in reason.lower()
        assert "dishonest" not in reason.lower()

def test_single_review_empty_cleaned_text_rejection():
    with pytest.raises(EmptyCleanedTextError):
        analyze_review("Helpful? 43\nRead More")

def test_single_review_endpoint_rejects_empty():
    response = client.post("/analyze", json={"text": "Helpful? 43\nRead More"})
    assert response.status_code == 400
    assert "No meaningful review text remained" in response.json()["detail"]


# ── 3. Batch Analysis Tests ─────────────────────────────────────────────────

def test_batch_counts_flagged_skipped_distribution():
    payload = {
        "reviews": [
            "This is a great product, highly recommend!",
            "   ",
            "Awesome product. Best purchase ever. Must buy.",
            "",
            "This is a standard product that works reasonably well.",
            "   \t\n   "
        ]
    }
    response = client.post("/analyze-batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    summary = data["summary"]
    results = data["results"]
    
    assert summary["reviews_submitted"] == 6
    assert summary["reviews_analyzed"] == 3
    assert summary["reviews_skipped"] == 3
    
    # Check distribution
    dist = summary["distribution"]
    assert sum(dist.values()) == summary["reviews_analyzed"]
    
    # Check pct_computer_generated calculation
    flagged = summary["count_flagged"]
    analyzed = summary["reviews_analyzed"]
    expected_pct = round((flagged / analyzed) * 100, 1)
    assert summary["pct_computer_generated"] == expected_pct

def test_batch_division_by_zero_guard():
    payload = {"reviews": ["", "  ", "\n"]}
    response = client.post("/analyze-batch", json=payload)
    assert response.status_code == 422
    assert "No meaningful review text" in response.json()["detail"]

def test_batch_size_limit_rejection():
    payload = {"reviews": ["test"] * 101}
    response = client.post("/analyze-batch", json=payload)
    assert response.status_code == 422

def test_batch_duplicate_detection_and_reasons():
    payload = {
        "reviews": [
            "Awesome product! Highly recommend.",
            "Awesome product! Highly recommend.",
            "This is a completely unique review.",
            "Awesome product! Highly recommend.  "
        ]
    }
    response = client.post("/analyze-batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    results = data["results"]
    summary = data["summary"]
    
    assert summary["duplicate_reviews"] == 3
    assert summary["duplicate_groups"] == 1
    
    assert results[0]["duplicate"] is True
    assert results[1]["duplicate"] is True
    assert results[3]["duplicate"] is True
    assert results[2]["duplicate"] is False
    
    assert results[0]["duplicate_group"] == "dup_1"
    assert results[1]["duplicate_group"] == "dup_1"
    assert results[3]["duplicate_group"] == "dup_1"
    
    assert "identical to another submitted review" in results[0]["reasons"][0]

def test_batch_original_index_preservation():
    payload = {
        "reviews": [
            "Review index 0",
            "   ",
            "Review index 2"
        ]
    }
    response = client.post("/analyze-batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    results = data["results"]
    assert results[0]["review_index"] == 0
    assert results[1]["review_index"] == 2


# ── 4. Star-Rating Cutoffs and Risk Bands ───────────────────────────────────

def test_band_39():
    assert assign_risk_band(39) == "Low"

def test_band_40():
    assert assign_risk_band(40) == "Moderate"

def test_band_69():
    assert assign_risk_band(69) == "Moderate"

def test_band_70():
    assert assign_risk_band(70) == "High"


# ── 5. Responsible Interpretation & Evidence Rules ──────────────────────────

def test_risk_interpretation_definitions():
    low = get_risk_interpretation(35)
    assert low["risk_band"] == "Low"
    assert "Few strong computer-generated" in low["headline"]
    assert "does not prove" in low["description"]

    mod = get_risk_interpretation(50)
    assert mod["risk_band"] == "Moderate"
    assert "mixture of ordinary" in mod["headline"]
    assert "evidence is mixed" in mod["description"]

    high = get_risk_interpretation(85)
    assert high["risk_band"] == "High"
    assert "strongly resembles" in high["headline"]
    assert "does not establish" in high["description"]

def test_unmeasured_patterns_safety():
    # Make sure we don't display unmeasured patterns in explanations
    res = analyze_review("A simple organic review text.")
    forbidden = [
        "perplexity", "burstiness", "sentence-length", "lexical diversity",
        "reviewer posting frequency", "account history", "verified-purchase",
        "device behaviour", "coordinated reviewer", "ip address"
    ]
    for r in res["reasons"]:
        for f in forbidden:
            assert f not in r.lower()

def test_safety_check_definitive_claims():
    # Safe checks for single reviews
    res1 = analyze_review("Outstanding product. Best purchase ever!")
    res2 = analyze_review("Worst item ever, do not buy.")
    
    def check_reasons(reasons):
        for reason in reasons:
            assert "confirmed fake" not in reason.lower()
            assert "definitely fake" not in reason.lower()
            assert "fraud detected" not in reason.lower()
            assert "reviewer is lying" not in reason.lower()
            
    check_reasons(res1["reasons"])
    check_reasons(res2["reasons"])

def test_batch_headline_pluralization_and_metadata():
    payload = {
        "reviews": [
            "Awesome product, highly recommend!", # flagged high or moderate
            "Awesome product, highly recommend!",
            "Terrible experience, completely broke."
        ]
    }
    response = client.post("/analyze-batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "headline" in data
    assert "overall_risk_label" in data["summary"]
    assert "flagged_percentage_label" in data["summary"]
    assert "sample_notice" in data["summary"]
    assert data["message"] == "Results describe only the reviews submitted for analysis and may not represent every review for the product."
    assert "fake" not in data["headline"].lower()

def test_pasted_cooling_pad_batch():
    reviews = [
        """PRAVEEN KUMAR
5 out of 5 starsBest Cooling pad out there
Reviewed in India on 15 August 2022
Verified Purchase
Came across this product while searching for a cooling pad for my 2 laptops- gaming and work laptops; which get heated up real quick while using it on a desk. Although there are a lot of cooling pad options out there, my efforts on finding a decent cooling that will be good to use for both types of usage was going in vain as my office laptop is 13" in size, and my old cooling pad laptop holder used to always come in the way and make it uncomfortable to use and my gaming laptop is an alienware 17" which is big and weighs quite a bit - so a cheaper laptop cooling pad that I used earlier was of no use literally.


Coming to this cooling pad, I felt the price was a bit high at first instance but after going through the features, I felt this would serve both my purpose, and to my pleasure it perfectly fits my requirement.

The packaging is very premium to say the least (loved the logo ribbon that was tied with the USB cable).


The first feature that really stood out which I didn't find in any of the cooling pads available on amazon till now was this elevation bracket; so basically it is a cooling pad cum a laptop holder which you can raise up and I can use the laptop in a relaxed posture. Now I can sit for long gaming/programming sessions without any stress on my body and also on my laptops, it is simply great! Plus the fans are so quiet that I sometimes check back if it is even ON... LOL :D

The phone holder is also an important addition to this cooling pad, it greatly helps me keep a tab on my phone while I get busy on my laptop.


The metal base built is quite sturdy and multiple adjustment angles provide the exact viewing angle that I need.

Being a professional gamer and a techie, I am enticed by the RGB but I like the minimalistic design and the RGB aspect in this cooling is just what I wanted. All-in-all, super happy to have this great cooling pad.

Read more
Best Cooling pad out there
Best Cooling pad out there
Best Cooling pad out there
Best Cooling pad out there
Best Cooling pad out there
Best Cooling pad out there
Best Cooling pad out there
17 people found this helpful
Helpful
Report""",

        """Arjun Mishra
4 out of 5 starsGood Build quality but read this before buying
Reviewed in India on 21 October 2023
Verified Purchase
So I ordered this laptop cooler because I don’t have AC room or anything and I used to get 80 degree temperatures on CPU and GPU after this temperature dropped by 3 or 4 degree only. Ya but this is good product as per build quality and ya after gaming it cools down laptop temperature within seconds Also this can support a laptop like ASUS Tuf Dash as in photo also That RGB light is not that much bright so don’t expect anything.

Good Build quality but read this before buying
8 people found this helpful
Helpful
Report""",

        """Purushottam paras
5 out of 5 starsBest Cooling Pad Everrrr!!!!!
Reviewed in India on 11 July 2026
Verified Purchase
This cooling pad is the best accessory product I have ever purchased the leg stand, are still intact and working after soo many years, and the cooling fans are working properly as well, the company has done a great job

Helpful
Report""",

        """Anubhav G.
1 out of 5 starsReal long term review- dont waste your money buy something else
Reviewed in India on 9 June 2025
Verified Purchase
Bought this as laptop (officially working laptop) use to just switch off or freeze. Bought in November 2024 where its almost winters in Northern India still 2 months into use the laptop still froze, the same laptop on some other non fan model laptop stand worked fine though. Now almost less than an year the fan went kaput as it started making loads of noise most likely a bearing issue. In summary don't buy this waste garbage chinese product (chala to chaand tak warna shaam tak) considering the exuberant cost its not worth the hard earned money. First of all, it is a gimmick with fans which doesn't work in the first place and secondly its not a long term solution ie wont work properly for even an year.

Money wasted=lesson learned.

2 people found this helpful
Helpful
Report""",

        """ANGER_MAN
5 out of 5 starsNice quality
Reviewed in India on 29 May 2026
Verified Purchase
Best build quality

Helpful
Report""",

        """anshu
5 out of 5 starsgo for it
Reviewed in India on 5 July 2026
Verified Purchase
very sturdy very strong just the fan speed could have been better and lower price like 17to1800

Helpful
Report""",

        """aaditya keshari
3 out of 5 starsGood Performance but Needs Improvement
Reviewed in India on 15 February 2026
Verified Purchase
I bought the Archer Tech Lab RGB Gaming Laptop Cooling Pad, and I am happy with it overall.The cooling pad works well and helps keep my laptop cool during long gaming and study sessions. The fans are strong and the airflow reduces heat. The RGB lights look cool and add style to my setup.The size fits most laptops and it feels sturdy. The USB connection is easy and doesn’t require extra power. It also has a comfortable angle for typing and gaming.One problem: sometimes it turns off automatically by itself. This can be annoying during long use.Overall, this cooling pad is useful for gamers and students who use laptops for long hours. It is good value for money, but the automatic shut-off issue should be improved.

One person found this helpful
Helpful
Report""",

        """GSingh
4 out of 5 starsGood Coolpad for laptops
Reviewed in India on 23 November 2024
Verified Purchase
Got this for about 2300. It's worth the money for it's design & various options to choose from.


This Coolpad has good features and works as advertised. However 17" laptop is hard to handle by this Coolpad since mly 17" laptop overflows the entire pad. It's not recommended to use this pad inclined with heavy or 17" laptop. In that case the laptop is pushed outside the pad, making this pad ineffective. That's why 4 stars else it's a awesome pad.


Size wize it's for 14" and upto 15.6" laptop sizes. LED is worthless while in use. Other features are good like it has a optional stand. It gives ventilation to the five fans.


Good design features include fan starts from highest speed to lowest, in that order. Fans are almost quiet. It has a phone tray for one slim phone. USB wire provided has sufficient length to cover breath of 17" & hence lower dimensions of laptops. This one is sturdy.


This one doesn't reduce temperature that much as my previous one. But, it's still effective since stand gives ventilation & even without opening stand, it's designed to suck air from down to up direction.


I like this Coolpad as it's comfortable while in use on the bed and with multiple options (stand / on table / phone / 7 inclines / fan speed).


One video review shkw the fans stopped working. It happened to me too, with laptop powering through usb. But, worked at lower speeds 1 &2. When I changed power source to 2.4 A usb, it works Ok.
"""
    ]
    
    payload = {"reviews": reviews}
    response = client.post("/analyze-batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    summary = data["summary"]
    results = data["results"]
    
    assert summary["reviews_submitted"] == 8
    assert summary["reviews_analyzed"] == 8
    assert summary["reviews_skipped"] == 0
    
    for idx, r in enumerate(results):
        assert len(r["cleaned_text"]) > 0
        assert r["review_index"] == idx
        # Ensure reasons cap at 3
        assert len(r["reasons"]) <= 3
        # Ensure safety constraints
        for reason in r["reasons"]:
            assert "confirmed fake" not in reason.lower()
            assert "definitely fake" not in reason.lower()
            assert "fraud detected" not in reason.lower()
            assert "reviewer is lying" not in reason.lower()


def test_ratings_validation():
    # 1. 1 accepted
    res = client.post("/analyze", json={"text": "A good review", "rating": 1})
    assert res.status_code == 200

    # 2. 5 accepted
    res = client.post("/analyze", json={"text": "A good review", "rating": 5})
    assert res.status_code == 200

    # 3. 0 rejected
    res = client.post("/analyze", json={"text": "A good review", "rating": 0})
    assert res.status_code == 422

    # 4. 6 rejected
    res = client.post("/analyze", json={"text": "A good review", "rating": 6})
    assert res.status_code == 422

    # 5. Negative rejected
    res = client.post("/analyze", json={"text": "A good review", "rating": -1})
    assert res.status_code == 422

    # 6. Non-numeric rejected
    res = client.post("/analyze", json={"text": "A good review", "rating": "five"})
    assert res.status_code == 422

    # 7. Missing accepted
    res = client.post("/analyze", json={"text": "A good review", "rating": None})
    assert res.status_code == 200


def test_batch_inputs():
    # 1. Empty rejected
    res = client.post("/analyze-batch", json={"reviews": []})
    assert res.status_code == 422

    # 2. Exactly 100 accepted
    res = client.post("/analyze-batch", json={"reviews": ["Valid text"] * 100})
    assert res.status_code == 200

    # 3. Over 100 rejected
    res = client.post("/analyze-batch", json={"reviews": ["Valid text"] * 101})
    assert res.status_code == 422

    # 4. All cleaned empty rejected
    res = client.post("/analyze-batch", json={"reviews": ["", "  "]})
    assert res.status_code == 422


def test_csv_upload_safety():
    # 1. Missing filename
    import io
    # 1. Missing filename (TestClient treats empty filename as text field -> 422)
    response = client.post("/analyze-csv", files={"file": ("", io.BytesIO(b"review_text\nHello"), "text/csv")})
    assert response.status_code == 422

    # 2. Uppercase extension
    csv_data = b"review_text,rating\nGreat product,5.0"
    response = client.post("/analyze-csv", files={"file": ("TEST.CSV", io.BytesIO(csv_data), "text/csv")})
    assert response.status_code == 200

    # 3. Wrong extension
    response = client.post("/analyze-csv", files={"file": ("test.txt", io.BytesIO(csv_data), "text/plain")})
    assert response.status_code == 422

    # 4. Invalid CSV
    response = client.post("/analyze-csv", files={"file": ("test.csv", io.BytesIO(b"review_text,rating\nhello\nworld,1,2"), "application/octet-stream")})
    assert response.status_code == 422
    assert "could not be parsed" in response.json()["detail"]

    # 5. Oversized upload
    oversized = io.BytesIO(b"a" * (5 * 1024 * 1024 + 2))
    response = client.post("/analyze-csv", files={"file": ("test.csv", oversized, "text/csv")})
    assert response.status_code == 413
    assert "exceeds the 5 MB upload limit" in response.json()["detail"]

    # 6. More than 1,000 rows
    many_rows = b"review_text\n" + b"some text\n" * 1001
    response = client.post("/analyze-csv", files={"file": ("test.csv", io.BytesIO(many_rows), "text/csv")})
    assert response.status_code == 422
    assert "contains more than 1000 rows" in response.json()["detail"]

    # 7. Missing review_text column
    bad_cols = b"content,rating\nGreat,5"
    response = client.post("/analyze-csv", files={"file": ("test.csv", io.BytesIO(bad_cols), "text/csv")})
    assert response.status_code == 422
    assert "must have a 'review_text' column" in response.json()["detail"]

    # 8. Optional ratings & invalid ratings & empty rows
    mixed_data = b"  review_text  ,  rating  \nGreat product,5.0\nBad item,6\nNeutral product,not-a-number\nEmpty row,\n\n"
    response = client.post("/analyze-csv", files={"file": ("test.csv", io.BytesIO(mixed_data), "text/csv")})
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 4
    assert results[0]["rating"] == 5
    assert results[1]["rating"] is None
    assert results[2]["rating"] is None
    assert results[3]["rating"] is None


def test_sentiment_compound():
    from signals.consistency import sentiment_compound
    # 1. returns native float
    score = sentiment_compound("This is a wonderful, fantastic and outstanding product!")
    assert isinstance(score, float)
    assert score > 0.0

    # 2. empty returns 0.0
    assert sentiment_compound("") == 0.0


def test_explanations_safety():
    # 1. Duplicate reason remains plain text and no internal reasons leak
    payload = {
        "reviews": [
            "This is a duplicate review text.",
            "This is a duplicate review text."
        ]
    }
    response = client.post("/analyze-batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "_reasons" not in data["results"][0]
    assert "identical to another" in data["results"][0]["reasons"][0]

