from pathlib import Path

from PIL import Image, ImageOps


SOURCE = Path(r"C:\Users\efily\Downloads\Telegram Desktop")
WORK_ASSETS = Path(__file__).resolve().parents[1] / "annaelle-work" / "assets"
IMAGE_ASSETS = Path(__file__).resolve().parents[1] / "images"
WEBP_OPTIONS = {"format": "WEBP", "quality": 88, "method": 6}


def open_rgb(name: str) -> Image.Image:
    with Image.open(SOURCE / name) as source:
        return ImageOps.exif_transpose(source).convert("RGB")


def save_width(image: Image.Image, destination: Path, width: int) -> None:
    height = round(image.height * width / image.width)
    resized = image.resize((width, height), Image.Resampling.LANCZOS)
    resized.save(destination, **WEBP_OPTIONS)


def save_fitted(image: Image.Image, destination: Path, size: tuple[int, int]) -> None:
    fitted = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    fitted.save(destination, **WEBP_OPTIONS)


gallery_order = [
    "IMG_1861.JPG",
    "IMG_1864.JPG",
    "IMG_1855.JPG",
    "IMG_1857.JPG",
    "IMG_1858.JPG",
    "IMG_1863.JPG",
    "800_8787-HDR.jpg",
    "800_9029-HDR.jpg",
]

for filename in gallery_order:
    image = open_rgb(filename)
    stem = Path(filename).stem.lower()
    save_fitted(image, WORK_ASSETS / f"gallery-{stem}-640.webp", (640, 1067))
    save_fitted(image, WORK_ASSETS / f"gallery-{stem}-1200.webp", (1200, 2000))

hero = open_rgb("IMG_1959.JPG")
save_width(hero, WORK_ASSETS / "hero-main-960.webp", 960)
save_width(hero, WORK_ASSETS / "hero-main-1800.webp", 1800)

offer_crops = {
    "IMG_3433.PNG": (56, 688, 1020, 1240),
    "IMG_3434.PNG": (34, 697, 1041, 1072),
}

for index, (filename, crop_box) in enumerate(offer_crops.items(), start=1):
    image = open_rgb(filename).crop(crop_box)
    canvas = Image.new("RGB", (760, 440), "#fef7fb")
    contained = ImageOps.contain(image, canvas.size, method=Image.Resampling.LANCZOS)
    canvas.paste(contained, ((canvas.width - contained.width) // 2, (canvas.height - contained.height) // 2))
    canvas.save(IMAGE_ASSETS / f"offer-new-{index}-760.webp", **WEBP_OPTIONS)
    canvas.resize((380, 220), Image.Resampling.LANCZOS).save(
        IMAGE_ASSETS / f"offer-new-{index}-380.webp", **WEBP_OPTIONS
    )

# The third poster mixes its photo collage with a large text label. Rebuild the
# thumbnail from the five clean photo areas so no poster copy leaks into the card.
poster = open_rgb("IMG_3435.PNG")
third_offer = Image.new("RGB", (760, 440), "#fef7fb")
photo_regions = [
    ((177, 663, 348, 872), (0, 0, 168, 208)),
    ((382, 663, 555, 872), (178, 0, 346, 208)),
    ((589, 663, 762, 872), (356, 0, 524, 208)),
    ((480, 910, 652, 1122), (178, 220, 382, 440)),
    ((701, 770, 997, 1127), (536, 48, 760, 440)),
]
for source_box, destination_box in photo_regions:
    destination_size = (
        destination_box[2] - destination_box[0],
        destination_box[3] - destination_box[1],
    )
    fragment = ImageOps.fit(
        poster.crop(source_box),
        destination_size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )
    third_offer.paste(fragment, destination_box[:2])

third_offer.save(IMAGE_ASSETS / "offer-new-3-760.webp", **WEBP_OPTIONS)
third_offer.resize((380, 220), Image.Resampling.LANCZOS).save(
    IMAGE_ASSETS / "offer-new-3-380.webp", **WEBP_OPTIONS
)

print("Prepared gallery, hero and offer WebP assets.")
