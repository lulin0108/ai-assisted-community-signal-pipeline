"use strict";

globalThis.commerceEvidence = {
  market: "United States",
  period: "2021-2025",
  example: "Find a small-batch product that keeps a pet feeding area tidy.",
  focusExamples: ["Find a way to drain water around a dog bowl.", "Find an easy-to-wash pet bowl mat.", "Find a pet feeding mat that holds up to chewing."],
  referenceImage: "https://neaterpets.com/cdn/shop/files/Neater_Feeder_Deluxe_Bottom_Basin.jpg?v=1689004483&width=640",
  products: [
    {id: "frisco", name: "Frisco Silicone Food Mat", format: "Flexible mat", source: "Chewy", url: "https://www.chewy.com/frisco-silicone-dog-cat-food-mat-blue/dp/389617", features: {catch: true, ownBowl: true, washable: true, drain: false, liftOut: false, reinforced: null}},
    {id: "petmaker", name: "Petmaker Non-Skid Tray", format: "Rigid tray", source: "Walmart", url: "https://www.walmart.com/ip/52385752", features: {catch: true, ownBowl: true, washable: true, drain: null, liftOut: null, reinforced: null}},
    {id: "neater", name: "Neater Feeder Deluxe", format: "Integrated feeder", source: "Neater Pets", url: "https://neaterpets.com/collections/neater-feeder/products/deluxe-neater-feeder", features: {catch: true, ownBowl: false, washable: true, drain: true, liftOut: null, reinforced: null}},
    {id: "waterboy", name: "Waterboy Portable Pet Bowl", format: "Portable bowl", source: "Chewy", url: "https://www.chewy.com/heininger-waterboy-portable-pet-bowl/product-reviews/159073", features: {catch: null, ownBowl: false, washable: null, drain: null, liftOut: null, reinforced: null}},
  ],
  feedback: [
    {id: "mat-daily-drying", product: "frisco", title: "Just as described", date: "2025-08-10", theme: "drain", stance: "support", note: "The mat stopped water soaking through from a cat's water bowl. The buyer still had to dry it at least daily.", url: "https://www.chewy.com/frisco-silicone-dog-cat-food-mat-blue/dp/389617"},
    {id: "mat-rinse", product: "frisco", title: "Great Food Mat for Cats", date: "2023-06-02", theme: "wash", stance: "support", note: "A buyer was happy with the spill-catching lip and reported rinsing and air-drying the mat three times a day.", url: "https://www.chewy.com/frisco-silicone-dog-cat-food-mat/dp/279505"},
    {id: "mat-wipe", product: "frisco", title: "Great mat, easy cleanup", date: "2021-02-18", theme: "wash", stance: "counter", note: "A buyer who switched from fabric found this silicone mat easy to wipe clean.", url: "https://www.chewy.com/frisco-silicone-dog-cat-food-mat/dp/279505"},
    {id: "mat-fit", product: "frisco", title: "Perfect size", date: "2025-12-02", theme: "wash", stance: "counter", note: "The buyer found the size suitable and the mat easy to clean after food and water spills.", url: "https://www.chewy.com/frisco-silicone-dog-cat-food-mat-blue/dp/389617"},
    {id: "mat-fountain", product: "frisco", title: "Perfect Floor Protection", date: "2025-12-24", theme: "drain", stance: "counter", note: "The buyer reported that splashes from an existing cat fountain stayed off the floor with the mat.", url: "https://www.chewy.com/frisco-silicone-dog-cat-food-mat/dp/279505"},
    {id: "mat-tear", product: "frisco", title: "Very nice looking but not durable", date: "2023-02-18", theme: "wear", stance: "support", note: "A piece of silicone tore after about two months under a fountain. The buyer was unsure what caused it.", url: "https://www.chewy.com/frisco-silicone-dog-cat-food-mat/dp/279505"},
    {id: "mat-chew", product: "frisco", title: "Loved the color", date: "2025-12-11", theme: "wear", stance: "support", note: "The mat caught water, but a puppy chewed pieces off it. The buyer planned to replace it.", url: "https://www.chewy.com/frisco-silicone-dog-cat-food-mat/dp/279505"},
    {id: "bowl-wash", product: "waterboy", title: "Good Product, tough to clean", date: "2025-10-26", theme: "wash", stance: "support", note: "A buyer of three portable bowls reported staining over time and difficulty cleaning the inside.", url: "https://www.chewy.com/heininger-waterboy-portable-pet-bowl/product-reviews/159073"},
  ],
  themes: [
    {id: "drain", label: "Pouring away pooled water", keywords: /\b(drain\w*|spill\w*|puddles?|splash\w*|pooled|water bowls?|existing bowls?)\b|\u6c34\u7897|\u6c34\u6e0d|\u79ef\u6c34|\u5012\u6c34|\u6ea2\u6c34|\u9632\u6e85/i},
    {id: "wash", label: "Cleaning and drying effort", keywords: /\b(clean\w*|wash\w*|scrub\w*|wipe\w*)\b|\u6e05\u6d01|\u6e05\u6d17|\u6613\u6d17/i},
    {id: "wear", label: "Tearing or chewing", keywords: /\b(chew\w*|tear\w*|durab\w*|wear|pupp(?:y|ies))\b|\u8010\u7528|\u5543\u54ac|\u6495\u88c2|\u9632\u54ac/i},
  ],
  features: {catch: "Spill barrier", ownBowl: "Keep own bowl", washable: "Dishwasher-safe", drain: "Drainage basin", liftOut: "Slide-out basin", reinforced: "Reinforced edge"},
  directions: [
    {id: "lift", title: "Slide-out drip tray", theme: "drain", audience: "Pet owners who want to keep their existing bowl and empty pooled water quickly.", features: ["ownBowl", "drain", "liftOut"], researchReason: "A buyer reported daily drying. Check whether a compatible slide-out basin already solves it.", next: "Check removable-basin designs that accept existing bowls, then confirm how often owners empty standing water.", priority: 0},
    {id: "rim", title: "Washable raised-edge mat", theme: "wash", audience: "Pet owners who want to contain spills and clean up after feeding.", features: ["catch", "ownBowl", "washable"], next: "Compare dishwashing and wipe-down effort before proposing a different surface or form.", priority: 1},
    {id: "edge", title: "Reinforced mat edge", theme: "wear", audience: "Owners replacing a mat that tears during use or is chewed at the edges.", features: ["catch", "reinforced"], next: "Separate normal wear from chewing and check durable alternatives before considering a design.", priority: 2},
  ],
};
