"""
Server-rendered public storefront.

Why this exists: Flet renders web output through Flutter's web engine,
which (as of the Flet version this project uses) draws to a canvas rather
than semantic HTML/DOM -- a search engine crawler fetching a Flet page
sees essentially no content. This router serves the read-only, publicly
interesting pages (home, category, product, search) as real server-rendered
HTML with proper meta tags and schema.org structured data, so MAUMart's
catalog is actually discoverable. Authenticated actions (login, cart,
checkout, dashboards) stay in the Flet app -- linked from every page here
via the "Open the app" call to action, matching how many real storefronts
split a crawlable catalog from an app-like authenticated experience.

Verify this is actually crawlable with: `curl http://.../store/` and read
the HTML directly -- no JavaScript execution needed to see the content,
unlike the Flet app.
"""
import os
import json as jsonlib
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape

from fastapi import APIRouter, Query, Request, Depends
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

import models
from database import get_db
from routers.listings import _to_out, with_relations, like_pattern

router = APIRouter(prefix="/store", tags=["storefront"])
# Absolute path: a relative "templates" only worked when the process was started from backend/.
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"))

PAGE_SIZE = 24
MAX_SITEMAP_URLS = 50000  # the sitemap protocol's per-file limit

APP_URL = os.environ.get("MAUMART_APP_URL", "http://127.0.0.1:8551")


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _common_ctx(request: Request):
    return {"app_url": APP_URL, "base_url": _base_url(request)}


def _safe_jsonld(data: dict) -> str:
    """
    Serialise for embedding inside <script type="application/ld+json">. json.dumps alone does NOT
    escape '</script>', so a vendor-chosen title like `x</script><script>alert(1)</script>` would
    break out of the tag (stored XSS on a public page). Escaping <, > and & as \\uXXXX is still
    valid JSON but can no longer terminate the element.
    """
    return (jsonlib.dumps(data)
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def _page_ctx(page: int, total: int) -> dict:
    return {"page": page, "has_prev": page > 1, "has_next": page * PAGE_SIZE < total, "total": total}


@router.get("/", response_class=HTMLResponse)
def store_home(request: Request, db: Session = Depends(get_db)):
    listings = with_relations(db.query(models.Listing)).filter(models.Listing.status == "live") \
        .order_by(models.Listing.sales_count.desc(), models.Listing.id).limit(12).all()
    return templates.TemplateResponse(request, "home.html", {
        **_common_ctx(request),
        "categories": models.CATEGORIES,
        "listings": [_to_out(l) for l in listings],
    })


@router.get("/category/{category}", response_class=HTMLResponse)
def store_category(category: str, request: Request, page: int = Query(default=1, ge=1, le=10000),
                   db: Session = Depends(get_db)):
    if category not in models.CATEGORIES:  # don't mint indexable pages for arbitrary URLs
        return HTMLResponse("<h1>Category not found</h1>", status_code=404)
    query = db.query(models.Listing).filter(models.Listing.status == "live", models.Listing.category == category)
    total = query.count()
    listings = with_relations(query).order_by(models.Listing.created_at.desc(), models.Listing.id) \
        .limit(PAGE_SIZE).offset((page - 1) * PAGE_SIZE).all()
    return templates.TemplateResponse(request, "category.html", {
        **_common_ctx(request), "category": category, "listings": [_to_out(l) for l in listings],
        "pager_base": f"/store/category/{quote(category)}?", **_page_ctx(page, total),
    })


@router.get("/search", response_class=HTMLResponse)
def store_search(request: Request, q: str = Query(min_length=1, max_length=100),
                 page: int = Query(default=1, ge=1, le=10000), db: Session = Depends(get_db)):
    like = like_pattern(q)
    query = db.query(models.Listing).filter(
        models.Listing.status == "live",
        or_(models.Listing.title.ilike(like, escape="\\"), models.Listing.description.ilike(like, escape="\\")),
    )
    total = query.count()
    listings = with_relations(query).order_by(models.Listing.sales_count.desc(), models.Listing.id) \
        .limit(PAGE_SIZE).offset((page - 1) * PAGE_SIZE).all()
    return templates.TemplateResponse(request, "search.html", {
        **_common_ctx(request), "query": q, "listings": [_to_out(l) for l in listings],
        "pager_base": f"/store/search?q={quote(q)}&", **_page_ctx(page, total),
    })


@router.get("/product/{listing_id}", response_class=HTMLResponse)
def store_product(listing_id: str, request: Request, db: Session = Depends(get_db)):
    listing = with_relations(db.query(models.Listing)).filter(models.Listing.id == listing_id).first()
    # Pending-review (e.g. pharmacy) and deactivated listings must not be publicly viewable.
    if not listing or listing.status != "live":
        return HTMLResponse("<h1>Listing not found</h1>", status_code=404)

    listing_out = _to_out(listing)
    avg, review_count = db.query(func.avg(models.Review.rating), func.count(models.Review.id)).filter(
        models.Review.vendor_id == listing.vendor_id).one()
    reviews = db.query(models.Review).filter(models.Review.vendor_id == listing.vendor_id) \
        .order_by(models.Review.created_at.desc()).limit(20).all()
    avg_rating = round(float(avg), 2) if avg is not None else None

    # schema.org Product/Offer structured data -- Unit 6.4's schema.org discussion,
    # applied for real: this is what actually earns rich results in search engines.
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": listing.title,
        "description": listing.description,
        "category": listing.category,
        "offers": {
            "@type": "Offer",
            "priceCurrency": "NGN",
            "price": str(listing.price),
            "availability": "https://schema.org/InStock" if listing.quantity > 0 else "https://schema.org/OutOfStock",
            "url": f"{_base_url(request)}/store/product/{listing.id}",
        },
        "seller": {"@type": "Organization", "name": listing.vendor.business_name},
    }
    if listing.photos:
        jsonld["image"] = [p.url for p in listing.photos]
    if avg_rating:
        jsonld["aggregateRating"] = {
            "@type": "AggregateRating", "ratingValue": str(avg_rating), "reviewCount": str(review_count),
        }

    return templates.TemplateResponse(request, "product.html", {
        **_common_ctx(request),
        "listing": listing_out, "avg_rating": avg_rating, "review_count": review_count,
        "reviews": reviews, "jsonld": _safe_jsonld(jsonld),
    })


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt(request: Request):
    return (
        "User-agent: *\n"
        "Allow: /store/\n"
        "Disallow: /auth/\n"
        "Disallow: /admin/\n"
        "Disallow: /users/\n"
        f"Sitemap: {_base_url(request)}/store/sitemap.xml\n"
    )


@router.get("/sitemap.xml")
def sitemap_xml(request: Request, db: Session = Depends(get_db)):
    base = _base_url(request)
    listing_ids = [r[0] for r in db.query(models.Listing.id).filter(models.Listing.status == "live")
                   .order_by(models.Listing.id).limit(MAX_SITEMAP_URLS - 20).all()]
    urls = [f"{base}/store/"] + [f"{base}/store/category/{quote(c)}" for c in models.CATEGORIES]
    urls += [f"{base}/store/product/{lid}" for lid in listing_ids]

    body = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        body.append(f"<url><loc>{xml_escape(u)}</loc></url>")
    body.append("</urlset>")
    return Response("\n".join(body), media_type="application/xml")
