import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import Address
from catalog.models import TCG, Category, Product, ProductImage, Inventory, Promotion, Review
from orders.models import StoreSettings, Order, OrderItem, OrderStatusHistory, Payment, Invoice, InvoiceItem
from wishlist.models import Wishlist

User = get_user_model()


class Command(BaseCommand):
    help = "Seed NovaChrono with rich collectible TCG data, users, and store settings."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("* Initializing NovaChrono Universe Data Seed..."))

        # 1. Store Settings
        settings_obj, _ = StoreSettings.objects.get_or_create(id=1)
        settings_obj.store_name = "NOVACHRONO"
        settings_obj.tagline = "Collect. Discover. Trade."
        settings_obj.address_line1 = "742 Nebula Way, Suite 400"
        settings_obj.address_line2 = "Collectors District"
        settings_obj.city = "San Francisco"
        settings_obj.state = "CA"
        settings_obj.postal_code = "94107"
        settings_obj.country = "United States"
        settings_obj.email = "support@novachrono.com"
        settings_obj.phone = "+1 (800) 555-CHRONO"
        settings_obj.website = "https://novachrono.com"
        settings_obj.tax_id = "US-EIN-94-2849201"
        settings_obj.default_tax_rate = Decimal('7.00')
        settings_obj.invoice_prefix = "NC-2026-"
        settings_obj.free_shipping_threshold = Decimal('150.00')
        settings_obj.standard_shipping_rate = Decimal('9.99')
        settings_obj.save()
        self.stdout.write(self.style.SUCCESS("[OK] Store settings configured."))

        # 2. Users
        # Super Admin
        super_admin, created = User.objects.get_or_create(username='superadmin', defaults={
            'email': 'admin@novachrono.com',
            'first_name': 'Nova',
            'last_name': 'Administrator',
            'role': User.Role.SUPERADMIN,
            'is_staff': True,
            'is_superuser': True,
        })
        if created:
            super_admin.set_password('admin123')
            super_admin.save()
            Wishlist.objects.get_or_create(user=super_admin)
            self.stdout.write(self.style.SUCCESS("[OK] Super Admin created: superadmin / admin123"))

        # Staff Member
        staff_user, created = User.objects.get_or_create(username='staff_alex', defaults={
            'email': 'alex@novachrono.com',
            'first_name': 'Alex',
            'last_name': 'Vance',
            'role': User.Role.STAFF,
            'is_staff': True,
        })
        if created:
            staff_user.set_password('staff123')
            staff_user.save()
            Wishlist.objects.get_or_create(user=staff_user)
            self.stdout.write(self.style.SUCCESS("[OK] Staff member created: staff_alex / staff123"))

        # Buyer User
        buyer_user, created = User.objects.get_or_create(username='collector_ash', defaults={
            'email': 'ash@novachrono.com',
            'first_name': 'Ash',
            'last_name': 'Ketchum',
            'role': User.Role.BUYER,
        })
        if created:
            buyer_user.set_password('buyer123')
            buyer_user.save()
            Wishlist.objects.get_or_create(user=buyer_user)
            self.stdout.write(self.style.SUCCESS("[OK] Buyer created: collector_ash / buyer123"))

        # Buyer Address
        address, _ = Address.objects.get_or_create(
            user=buyer_user,
            full_name="Ash Ketchum",
            defaults={
                'phone': "+1 (555) 987-6543",
                'address_line1': "12 Pallet Town Avenue",
                'address_line2': "Apt 4B",
                'city': "San Jose",
                'state': "CA",
                'postal_code': "95112",
                'country': "United States",
                'is_default_shipping': True,
                'is_default_billing': True,
            }
        )

        # 3. Promotions
        Promotion.objects.get_or_create(
            code='NOVA10',
            defaults={
                'discount_percentage': Decimal('10.00'),
                'minimum_spend': Decimal('50.00'),
                'is_active': True,
            }
        )
        Promotion.objects.get_or_create(
            code='CHRONO25',
            defaults={
                'discount_amount': Decimal('25.00'),
                'minimum_spend': Decimal('150.00'),
                'is_active': True,
            }
        )
        Promotion.objects.get_or_create(
            code='FIRSTDROP',
            defaults={
                'discount_percentage': Decimal('15.00'),
                'minimum_spend': Decimal('100.00'),
                'is_active': True,
            }
        )

        # 4. TCG Universes
        tcgs_data = [
            {
                'name': 'Pokémon',
                'slug': 'pokemon',
                'icon_symbol': '⚡',
                'accent_color': '#FFB800',
                'banner_image': 'https://images.unsplash.com/photo-1613771404784-3a5686aa2be3?w=1200&auto=format&fit=crop&q=80',
                'description': 'The world’s most iconic monster franchise. Discover vintage base sets, contemporary expansion booster boxes, and coveted illustration rares.',
                'display_order': 1,
            },
            {
                'name': 'One Piece',
                'slug': 'one-piece',
                'icon_symbol': '🏴‍☠️',
                'accent_color': '#E53935',
                'banner_image': 'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=1200&auto=format&fit=crop&q=80',
                'description': 'The explosive Manga sensation by Eiichiro Oda. High-stakes leader cards, manga rares, and competitive sealed cases.',
                'display_order': 2,
            },
            {
                'name': 'Yu-Gi-Oh!',
                'slug': 'yu-gi-oh',
                'icon_symbol': '👁️',
                'accent_color': '#8E24AA',
                'banner_image': 'https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=1200&auto=format&fit=crop&q=80',
                'description': 'It’s time to duel! Quarter Century Secret Rares, legendary duelists packs, and nostalgic retro sealed boxes.',
                'display_order': 3,
            },
            {
                'name': 'Magic: The Gathering',
                'slug': 'magic-the-gathering',
                'icon_symbol': '✨',
                'accent_color': '#FB8C00',
                'banner_image': 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1200&auto=format&fit=crop&q=80',
                'description': 'The progenitor of trading card games. Commander decks, serialized collector booster boxes, and mythic borderless planeswalkers.',
                'display_order': 4,
            },
            {
                'name': 'Dragon Ball Super',
                'slug': 'dragon-ball',
                'icon_symbol': '🐉',
                'accent_color': '#FF5722',
                'banner_image': 'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1200&auto=format&fit=crop&q=80',
                'description': 'Saiyan fury unlocked. Collector booster boxes, God Rare chase pulls, and dynamic anime battle art.',
                'display_order': 5,
            },
            {
                'name': 'Gundam Card Game',
                'slug': 'gundam',
                'icon_symbol': '🤖',
                'accent_color': '#0288D1',
                'banner_image': 'https://images.unsplash.com/photo-1563089145-599997674d42?w=1200&auto=format&fit=crop&q=80',
                'description': 'Mobile suit warfare in card form. Limited mechanical foil prints, pilot secret rares, and collector display sets.',
                'display_order': 6,
            },
        ]

        tcg_map = {}
        for t_data in tcgs_data:
            tcg_obj, _ = TCG.objects.update_or_create(slug=t_data['slug'], defaults=t_data)
            tcg_map[t_data['slug']] = tcg_obj

        # 5. Categories
        cats_data = [
            {'name': 'Booster Boxes', 'slug': 'booster-boxes', 'display_order': 1, 'description': 'Full factory-sealed displays containing 24-36 booster packs.'},
            {'name': 'Booster Packs', 'slug': 'booster-packs', 'display_order': 2, 'description': 'Individual sealed foil packs ready for fresh pulls.'},
            {'name': 'Elite Trainer Boxes', 'slug': 'elite-trainer-boxes', 'display_order': 3, 'description': 'Collector bundles loaded with packs, dice, card sleeves, and promo cards.'},
            {'name': 'Collections', 'slug': 'collections', 'display_order': 4, 'description': 'Curated gift tins, premium collection boxes, and exclusive drop sets.'},
            {'name': 'Singles', 'slug': 'singles', 'display_order': 5, 'description': 'Individual graded slabs and near-mint chase cards.'},
            {'name': 'Accessories', 'slug': 'accessories', 'display_order': 6, 'description': 'Tournament-grade sleeves, magnetic slabs, leather deck boxes, and playmats.'},
            {'name': 'Pre-Orders', 'slug': 'pre-orders', 'display_order': 7, 'description': 'Reserve upcoming global expansion sets before release dates.'},
            {'name': 'Mystery Products', 'slug': 'mystery-products', 'display_order': 8, 'description': 'Curated high-tier blind drops containing guaranteed vintage or graded cards.'},
        ]

        cat_map = {}
        for c_data in cats_data:
            cat_obj, _ = Category.objects.update_or_create(slug=c_data['slug'], defaults=c_data)
            cat_map[c_data['slug']] = cat_obj

        # 6. Comprehensive Products Seed (22 curated items)
        products_seed = [
            # Pokemon
            {
                'name': 'Pokémon 151 Booster Box (Japanese Import)',
                'sku': 'PKMN-151-BB-JA',
                'tcg': tcg_map['pokemon'],
                'category': cat_map['booster-boxes'],
                'price': Decimal('189.99'),
                'compare_at_price': Decimal('220.00'),
                'short_description': 'The iconic Scarlet & Violet Pokémon 151 Japanese expansion featuring Master Ball reverse holos.',
                'description': 'Experience the pinnacle of modern Pokémon card collecting. This factory-sealed Japanese Pokémon 151 booster box contains 20 packs with 7 cards per pack. Chase the coveted Erika’s Invitation Special Illustration Rare, Mew ex, and reverse holo Master Ball foil patterns on all original 151 Kanto Pokémon. Direct import from Japan, guaranteed unweighted and factory shrink-wrapped.',
                'product_type': Product.ProductType.BOOSTER_BOX,
                'condition': Product.Condition.SEALED,
                'language': Product.Language.JAPANESE,
                'edition': '1st Print Run',
                'is_featured': True,
                'is_new': True,
                'is_preorder': False,
                'stock': 24,
                'images': [
                    'https://images.unsplash.com/photo-1613771404784-3a5686aa2be3?w=800&auto=format&fit=crop&q=80',
                    'https://images.unsplash.com/photo-1542751371-adc38448a05e?w=800&auto=format&fit=crop&q=80'
                ]
            },
            {
                'name': 'Crown Zenith Pokémon Center Elite Trainer Box',
                'sku': 'PKMN-CZ-ETB-PC',
                'tcg': tcg_map['pokemon'],
                'category': cat_map['elite-trainer-boxes'],
                'price': Decimal('119.50'),
                'compare_at_price': Decimal('135.00'),
                'short_description': 'Exclusive Pokémon Center edition with 12 Crown Zenith booster packs and Lucario VSTAR promo.',
                'description': 'Celebrate the Sword & Shield era finale with the Crown Zenith Pokémon Center Elite Trainer Box. Features 12 booster packs, an etched Lucario VSTAR promo card featuring the exclusive Pokémon Center stamp, deck shields, acrylic condition markers, and a sturdy storage box with cosmic foil dividers.',
                'product_type': Product.ProductType.ELITE_TRAINER_BOX,
                'condition': Product.Condition.SEALED,
                'language': Product.Language.ENGLISH,
                'edition': 'Pokémon Center Exclusive',
                'is_featured': True,
                'is_new': False,
                'is_preorder': False,
                'stock': 12,
                'images': [
                    'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800&auto=format&fit=crop&q=80',
                ]
            },
            {
                'name': 'Charizard ex Special Illustration Rare #223 (PSA 10)',
                'sku': 'PKMN-151-CHAR-PSA10',
                'tcg': tcg_map['pokemon'],
                'category': cat_map['singles'],
                'price': Decimal('349.00'),
                'compare_at_price': Decimal('390.00'),
                'short_description': 'Graded Gem Mint PSA 10 Charizard ex obsidian flame illustration rare.',
                'description': 'A modern holy grail. Graded a pristine Gem Mint PSA 10, this Charizard ex features breathtaking full-bleed artwork depicting the fire dragon ascending from an active volcanic crater. Encapsulated in PSA UV-resistant archival sonically-sealed casing with certification verification barcode.',
                'product_type': Product.ProductType.SINGLE_CARD,
                'condition': Product.Condition.GRADED_PSA,
                'language': Product.Language.ENGLISH,
                'edition': 'Scarlet & Violet 151',
                'is_featured': True,
                'is_new': False,
                'is_preorder': False,
                'stock': 3,
                'images': [
                    'https://images.unsplash.com/photo-1563089145-599997674d42?w=800&auto=format&fit=crop&q=80',
                ]
            },
            {
                'name': 'Prismatic Evolutions Booster Display [PRE-ORDER]',
                'sku': 'PKMN-PRE-PRISM-BB',
                'tcg': tcg_map['pokemon'],
                'category': cat_map['pre-orders'],
                'price': Decimal('164.99'),
                'compare_at_price': Decimal('180.00'),
                'short_description': 'Upcoming Eeveelutions special booster box drop. Expected shipping Winter 2026.',
                'description': 'Reserve the most anticipated Pokémon release of the year! Focused on the beloved evolutions of Eevee, with Stellar Tera ex cards and rainbow foil alternate arts. Guaranteed allocation directly through NovaChrono distributor contracts.',
                'product_type': Product.ProductType.PRE_ORDER,
                'condition': Product.Condition.SEALED,
                'language': Product.Language.ENGLISH,
                'edition': '1st Edition Pre-Release',
                'is_featured': True,
                'is_new': True,
                'is_preorder': True,
                'stock': 50,
                'images': [
                    'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&auto=format&fit=crop&q=80',
                ]
            },

            # One Piece
            {
                'name': 'One Piece OP-05 Awakening of the New Era Booster Box',
                'sku': 'OP-OP05-BB-EN',
                'tcg': tcg_map['one-piece'],
                'category': cat_map['booster-boxes'],
                'price': Decimal('245.00'),
                'compare_at_price': Decimal('290.00'),
                'short_description': 'Contains the legendary Manga Gear 5 Luffy and anniversary signature cards.',
                'description': 'The most celebrated One Piece Card Game expansion to date! Commemorating the 1st anniversary, OP-05 features the holy grail Manga Rare Gear 5 Monkey D. Luffy signed by Eiichiro Oda, alongside alt-art Kid, Law, and Enel leaders. 24 booster packs per box.',
                'product_type': Product.ProductType.BOOSTER_BOX,
                'condition': Product.Condition.SEALED,
                'language': Product.Language.ENGLISH,
                'edition': '1st Anniversary Edition',
                'is_featured': True,
                'is_new': False,
                'is_preorder': False,
                'stock': 14,
                'images': [
                    'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800&auto=format&fit=crop&q=80',
                ]
            },
            {
                'name': 'One Piece OP-07 500 Years in the Future Booster Box',
                'sku': 'OP-OP07-BB-EN',
                'tcg': tcg_map['one-piece'],
                'category': cat_map['booster-boxes'],
                'price': Decimal('139.99'),
                'compare_at_price': Decimal('155.00'),
                'short_description': 'Egghead arc characters with Vegapunk, Jewelry Bonney, and Manga Boa Hancock.',
                'description': 'Dive into the futuristic scientific island of Egghead! OP-07 brings revolutionary deck archetypes featuring Dr. Vegapunk and his satellite clones, Boa Hancock manga rare, and incredible battle leader foils.',
                'product_type': Product.ProductType.BOOSTER_BOX,
                'condition': Product.Condition.SEALED,
                'language': Product.Language.ENGLISH,
                'edition': 'Original English Run',
                'is_featured': False,
                'is_new': True,
                'is_preorder': False,
                'stock': 18,
                'images': [
                    'https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=800&auto=format&fit=crop&q=80',
                ]
            },
            {
                'name': 'Roronoa Zoro Manga Rare Alt-Art (PSA 10)',
                'sku': 'OP-OP06-ZORO-PSA10',
                'tcg': tcg_map['one-piece'],
                'category': cat_map['singles'],
                'price': Decimal('899.00'),
                'compare_at_price': Decimal('999.00'),
                'short_description': 'Flawless PSA 10 Manga Foil Zoro from Wings of the Captain.',
                'description': 'An extraordinary collector grail. The iconic three-sword style master Roronoa Zoro in crisp manga panel background foil. Graded PSA 10 Gem Mint. Authenticated and securely stored in the NovaChrono climate-controlled vault.',
                'product_type': Product.ProductType.SINGLE_CARD,
                'condition': Product.Condition.GRADED_PSA,
                'language': Product.Language.ENGLISH,
                'edition': 'Wings of the Captain OP-06',
                'is_featured': True,
                'is_new': False,
                'is_preorder': False,
                'stock': 1,
                'images': [
                    'https://images.unsplash.com/photo-1542751371-adc38448a05e?w=800&auto=format&fit=crop&q=80',
                ]
            },

            # Yu-Gi-Oh!
            {
                'name': 'Yu-Gi-Oh! 25th Anniversary Rarity Collection II Box',
                'sku': 'YGO-RC02-BB-EN',
                'tcg': tcg_map['yu-gi-oh'],
                'category': cat_map['booster-boxes'],
                'price': Decimal('84.99'),
                'compare_at_price': Decimal('99.99'),
                'short_description': 'Every card upgraded with 7 rarity foil treatments including Quarter Century Secret Rare.',
                'description': 'The all-foil blockbuster is back! Rarity Collection II features 79 of the game’s most popular tournament staples, each printed in 7 luxurious foil finishes: Super Rare, Ultra Rare, Secret Rare, Platinum Secret Rare, Collector’s Rare, Ultimate Rare, and 25th Quarter Century Secret Rare.',
                'product_type': Product.ProductType.BOOSTER_BOX,
                'condition': Product.Condition.SEALED,
                'language': Product.Language.ENGLISH,
                'edition': '25th Anniversary Edition',
                'is_featured': True,
                'is_new': True,
                'is_preorder': False,
                'stock': 22,
                'images': [
                    'https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=800&auto=format&fit=crop&q=80',
                ]
            },
            {
                'name': 'Blue-Eyes White Dragon DDS-001 Retro Collector Slab',
                'sku': 'YGO-BEWD-DDS001-BGS',
                'tcg': tcg_map['yu-gi-oh'],
                'category': cat_map['singles'],
                'price': Decimal('1450.00'),
                'compare_at_price': Decimal('1600.00'),
                'short_description': 'Holy grail vintage Dark Duel Stories promo card graded BGS 9.0 Mint.',
                'description': 'The definitive holy grail of Yu-Gi-Oh! collecting. The vintage 2002 Dark Duel Stories prismatic secret rare Blue-Eyes White Dragon. Featuring vibrant diamond cross-hatch foil and museum-grade subgrades from Beckett Grading Services.',
                'product_type': Product.ProductType.SINGLE_CARD,
                'condition': Product.Condition.GRADED_BGS,
                'language': Product.Language.ENGLISH,
                'edition': 'Vintage Dark Duel Stories Promo',
                'is_featured': True,
                'is_new': False,
                'is_preorder': False,
                'stock': 1,
                'images': [
                    'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&auto=format&fit=crop&q=80',
                ]
            },

            # Magic: The Gathering
            {
                'name': 'Magic: The Gathering Modern Horizons 3 Collector Booster Box',
                'sku': 'MTG-MH3-CBB-EN',
                'tcg': tcg_map['magic-the-gathering'],
                'category': cat_map['booster-boxes'],
                'price': Decimal('389.99'),
                'compare_at_price': Decimal('440.00'),
                'short_description': '12 packs loaded with serialized cards, borderless fetchlands, and textured foils.',
                'description': 'The premier modern MtG powerhouse. Modern Horizons 3 Collector Booster Display includes 12 packs packed with rare and mythic cards, retro frame reprints, borderless profile treatments, and serialized double rainbow Eldrazi.',
                'product_type': Product.ProductType.BOOSTER_BOX,
                'condition': Product.Condition.SEALED,
                'language': Product.Language.ENGLISH,
                'edition': 'Collector Edition Print',
                'is_featured': True,
                'is_new': False,
                'is_preorder': False,
                'stock': 8,
                'images': [
                    'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&auto=format&fit=crop&q=80',
                ]
            },
            {
                'name': 'The Lord of the Rings: Tales of Middle-earth Collector Display',
                'sku': 'MTG-LOTR-CBB-EN',
                'tcg': tcg_map['magic-the-gathering'],
                'category': cat_map['booster-boxes'],
                'price': Decimal('475.00'),
                'compare_at_price': Decimal('520.00'),
                'short_description': 'Special edition collector display with borderless scene cards and foil rings.',
                'description': 'Immerse yourself in Middle-earth with Magic’s historic crossover. Features traditional foil Sol Rings in Elven, Dwarven, and Human scripts, alongside breathtaking panorama scene cards and foil-etched Nazgûl.',
                'product_type': Product.ProductType.BOOSTER_BOX,
                'condition': Product.Condition.SEALED,
                'language': Product.Language.ENGLISH,
                'edition': 'Universes Beyond Special Edition',
                'is_featured': False,
                'is_new': False,
                'is_preorder': False,
                'stock': 5,
                'images': [
                    'https://images.unsplash.com/photo-1563089145-599997674d42?w=800&auto=format&fit=crop&q=80',
                ]
            },

            # Dragon Ball Super
            {
                'name': 'Dragon Ball Super Fusion World: Awakened Pulse Booster Box',
                'sku': 'DBS-FB01-BB-EN',
                'tcg': tcg_map['dragon-ball'],
                'category': cat_map['booster-boxes'],
                'price': Decimal('115.00'),
                'compare_at_price': Decimal('130.00'),
                'short_description': 'Debut expansion for Fusion World with God Rare Son Goku alt-art.',
                'description': 'The launch set for the high-octane Fusion World system! Packed with legendary Z-Fighters, Super Saiyan transformations, energy markers, and the ultra-rare God Rare Son Goku with gilded foil stamping.',
                'product_type': Product.ProductType.BOOSTER_BOX,
                'condition': Product.Condition.SEALED,
                'language': Product.Language.ENGLISH,
                'edition': 'FB-01 1st Edition',
                'is_featured': True,
                'is_new': True,
                'is_preorder': False,
                'stock': 16,
                'images': [
                    'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800&auto=format&fit=crop&q=80',
                ]
            },
            {
                'name': 'Son Goku Secret Rare God Rare (PSA 10 Gem Mint)',
                'sku': 'DBS-FB01-GOKU-PSA10',
                'tcg': tcg_map['dragon-ball'],
                'category': cat_map['singles'],
                'price': Decimal('780.00'),
                'compare_at_price': Decimal('890.00'),
                'short_description': 'PSA 10 Gem Mint God Rare Goku with iridescent gold calligraphy stamping.',
                'description': 'One of the rarest pulls in modern anime trading card history. Beautifully preserved in a PSA 10 casing, this God Rare features holographic energy aura lines and signature gold foil highlights.',
                'product_type': Product.ProductType.SINGLE_CARD,
                'condition': Product.Condition.GRADED_PSA,
                'language': Product.Language.ENGLISH,
                'edition': 'Awakened Pulse FB01',
                'is_featured': False,
                'is_new': False,
                'is_preorder': False,
                'stock': 2,
                'images': [
                    'https://images.unsplash.com/photo-1613771404784-3a5686aa2be3?w=800&auto=format&fit=crop&q=80',
                ]
            },

            # Gundam Card Game
            {
                'name': 'Gundam Card Game Edition Beta Starter & Booster Set',
                'sku': 'GD-BETA-BUNDLE-EN',
                'tcg': tcg_map['gundam'],
                'category': cat_map['collections'],
                'price': Decimal('95.00'),
                'compare_at_price': Decimal('110.00'),
                'short_description': 'Limited Beta release featuring RX-78-2 and Wing Zero holographic promos.',
                'description': 'The tactical mech card game from Bandai! This bundle includes the two-player Starter Deck plus 6 sealed Beta booster packs. Features full-bleed mechanical illustrations of iconic mobile suits from Mobile Suit Gundam, Zeta, and Wing.',
                'product_type': Product.ProductType.COLLECTION_BOX,
                'condition': Product.Condition.SEALED,
                'language': Product.Language.ENGLISH,
                'edition': 'Beta Early Access Drop',
                'is_featured': True,
                'is_new': True,
                'is_preorder': False,
                'stock': 20,
                'images': [
                    'https://images.unsplash.com/photo-1563089145-599997674d42?w=800&auto=format&fit=crop&q=80',
                ]
            },

            # Accessories & Supplies
            {
                'name': 'NovaChrono Cosmic Shield Matte Sleeves (100-Pack)',
                'sku': 'ACC-SLV-COSMIC-100',
                'tcg': tcg_map['pokemon'],
                'category': cat_map['accessories'],
                'price': Decimal('14.99'),
                'compare_at_price': Decimal('18.00'),
                'short_description': 'Archival-grade textured matte sleeves engineered for effortless shuffle feel.',
                'description': 'Protect your prized cards with NovaChrono’s proprietary Cosmic Shield sleeves. Crystal-clear front window with deep black matte back texture. Acid-free, non-PVC polypropylene material prevents clouding and edge-wear over years of play.',
                'product_type': Product.ProductType.SLEEVES,
                'condition': Product.Condition.SEALED,
                'language': Product.Language.ENGLISH,
                'edition': 'Pro Edition Supplies',
                'is_featured': False,
                'is_new': True,
                'is_preorder': False,
                'stock': 120,
                'images': [
                    'https://images.unsplash.com/photo-1542751371-adc38448a05e?w=800&auto=format&fit=crop&q=80',
                ]
            },
            {
                'name': 'Chrono Vault 9-Pocket Zip Binder (360 Card Capacity)',
                'sku': 'ACC-BND-CHRONO-360',
                'tcg': tcg_map['one-piece'],
                'category': cat_map['accessories'],
                'price': Decimal('34.99'),
                'compare_at_price': Decimal('42.00'),
                'short_description': 'Water-resistant vegan leather binder with padded sides and heavy-duty zipper.',
                'description': 'The ultimate safehouse for master sets. Features 20 side-loading 9-pocket pages capable of holding 360 double-sleeved cards. Heavy-duty water-resistant exterior with debossed NovaChrono celestial star emblem and smooth orbital zipper pull.',
                'product_type': Product.ProductType.BINDERS,
                'condition': Product.Condition.SEALED,
                'language': Product.Language.ENGLISH,
                'edition': 'Signature Series',
                'is_featured': True,
                'is_new': True,
                'is_preorder': False,
                'stock': 35,
                'images': [
                    'https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=800&auto=format&fit=crop&q=80',
                ]
            },
            {
                'name': 'Magnetic Touch Card Slab Holders (5-Pack with UV Guard)',
                'sku': 'ACC-MAG-SLAB-5PK',
                'tcg': tcg_map['yu-gi-oh'],
                'category': cat_map['accessories'],
                'price': Decimal('19.99'),
                'compare_at_price': Decimal('24.00'),
                'short_description': '35pt diamond-corner magnetic card holders with 99% UV resistance.',
                'description': 'Museum quality showcase display for your raw singles. Extra-strong magnetic closure prevents accidental opening, while recessed arrowhead corners protect card edges from compression damage.',
                'product_type': Product.ProductType.ACCESSORIES,
                'condition': Product.Condition.SEALED,
                'language': Product.Language.ENGLISH,
                'edition': 'Standard 35pt Display',
                'is_featured': False,
                'is_new': False,
                'is_preorder': False,
                'stock': 60,
                'images': [
                    'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&auto=format&fit=crop&q=80',
                ]
            },
            {
                'name': 'Celestial Nebula Stitched-Edge Playmat',
                'sku': 'ACC-MAT-NEBULA-01',
                'tcg': tcg_map['magic-the-gathering'],
                'category': cat_map['accessories'],
                'price': Decimal('28.50'),
                'compare_at_price': Decimal('35.00'),
                'short_description': 'Premium 24x14 inch neoprene gaming playmat with anti-fray stitched perimeter.',
                'description': 'Smooth micro-fiber cloth top provides optimal glide for cards while anti-slip rubber backing stays firmly anchored on any tournament table. Features rich cosmic galaxy artwork created exclusively for NovaChrono.',
                'product_type': Product.ProductType.PLAYMATS,
                'condition': Product.Condition.SEALED,
                'language': Product.Language.ENGLISH,
                'edition': 'NovaChrono Original Art',
                'is_featured': False,
                'is_new': True,
                'is_preorder': False,
                'stock': 25,
                'images': [
                    'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800&auto=format&fit=crop&q=80',
                ]
            },

            # Mystery Drops
            {
                'name': 'NovaChrono High-Roller Mystery Vault Crate',
                'sku': 'MYS-VAULT-CRATE-01',
                'tcg': tcg_map['pokemon'],
                'category': cat_map['mystery-products'],
                'price': Decimal('299.99'),
                'compare_at_price': Decimal('350.00'),
                'short_description': 'Guaranteed 1x PSA 10 slab + 3 vintage/modern sealed packs + custom accessories.',
                'description': 'Experience the thrill of a premier high-tier unboxing! Each hand-assembled NovaChrono Mystery Vault Crate contains: 1 guaranteed PSA or BGS Gem Mint graded slab, 3 factory sealed booster packs spanning vintage to modern, 1 set of cosmic sleeves, and a 1-in-10 chance of pulling a vintage Base Set pack.',
                'product_type': Product.ProductType.MYSTERY,
                'condition': Product.Condition.SEALED,
                'language': Product.Language.ENGLISH,
                'edition': 'Limited Run of 100 Crates',
                'is_featured': True,
                'is_new': True,
                'is_preorder': False,
                'stock': 15,
                'images': [
                    'https://images.unsplash.com/photo-1613771404784-3a5686aa2be3?w=800&auto=format&fit=crop&q=80',
                ]
            },
            {
                'name': 'One Piece Two Legends OP-08 Booster Box [PRE-ORDER]',
                'sku': 'OP-OP08-BB-PRE',
                'tcg': tcg_map['one-piece'],
                'category': cat_map['pre-orders'],
                'price': Decimal('149.99'),
                'compare_at_price': Decimal('165.00'),
                'short_description': 'Featuring Rayleigh and Edward Newgate. Pre-order price guarantee.',
                'description': 'Witness the clash of legends! OP-08 Two Legends shines the spotlight on the Roger and Whitebeard Pirates with revolutionary dual-color leaders and breathtaking manga chase foils.',
                'product_type': Product.ProductType.PRE_ORDER,
                'condition': Product.Condition.SEALED,
                'language': Product.Language.ENGLISH,
                'edition': 'English 1st Print Run',
                'is_featured': False,
                'is_new': True,
                'is_preorder': True,
                'stock': 40,
                'images': [
                    'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800&auto=format&fit=crop&q=80',
                ]
            },
            {
                'name': 'Pokémon Paldean Fates Booster Bundle (6 Packs)',
                'sku': 'PKMN-PF-BUNDLE-6PK',
                'tcg': tcg_map['pokemon'],
                'category': cat_map['booster-packs'],
                'price': Decimal('32.99'),
                'compare_at_price': Decimal('38.00'),
                'short_description': 'Shiny Pokémon galore! 6 factory sealed Paldean Fates booster packs.',
                'description': 'Chase over 120 Shiny Pokémon in Paldean Fates! Includes Shiny Mew ex, Shiny Gardevoir ex, and the majestic dark tera Shiny Charizard ex. Perfect compact bundle for opening or long-term sealed storage.',
                'product_type': Product.ProductType.BOOSTER_PACK,
                'condition': Product.Condition.SEALED,
                'language': Product.Language.ENGLISH,
                'edition': 'Special Expansion',
                'is_featured': False,
                'is_new': False,
                'is_preorder': False,
                'stock': 30,
                'images': [
                    'https://images.unsplash.com/photo-1613771404784-3a5686aa2be3?w=800&auto=format&fit=crop&q=80',
                ]
            },
            {
                'name': 'Yu-Gi-Oh! Legend of Blue Eyes White Dragon 25th Reprint Box',
                'sku': 'YGO-LOB-25TH-BB',
                'tcg': tcg_map['yu-gi-oh'],
                'category': cat_map['booster-boxes'],
                'price': Decimal('79.99'),
                'compare_at_price': Decimal('90.00'),
                'short_description': 'The set that started it all in 2002. Re-released in original 24-pack configuration.',
                'description': 'Relive the genesis of Yu-Gi-Oh! 24 booster packs containing iconic vintage cards: Exodia the Forbidden One pieces, Blue-Eyes White Dragon, Red-Eyes Black Dragon, Dark Magician, and Monster Reborn.',
                'product_type': Product.ProductType.BOOSTER_BOX,
                'condition': Product.Condition.SEALED,
                'language': Product.Language.ENGLISH,
                'edition': '25th Anniversary Edition',
                'is_featured': False,
                'is_new': False,
                'is_preorder': False,
                'stock': 19,
                'images': [
                    'https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=800&auto=format&fit=crop&q=80',
                ]
            }
        ]

        for p_item in products_seed:
            prod, _ = Product.objects.update_or_create(
                sku=p_item['sku'],
                defaults={
                    'name': p_item['name'],
                    'tcg': p_item['tcg'],
                    'category': p_item['category'],
                    'price': p_item['price'],
                    'compare_at_price': p_item.get('compare_at_price'),
                    'short_description': p_item['short_description'],
                    'description': p_item['description'],
                    'product_type': p_item['product_type'],
                    'condition': p_item['condition'],
                    'language': p_item['language'],
                    'edition': p_item['edition'],
                    'is_featured': p_item['is_featured'],
                    'is_new': p_item['is_new'],
                    'is_preorder': p_item['is_preorder'],
                    'is_active': True,
                    'release_date': date.today() + (timedelta(days=45) if p_item['is_preorder'] else timedelta(days=-30)),
                }
            )

            # Inventory
            inv, _ = Inventory.objects.get_or_create(product=prod)
            inv.stock_quantity = p_item['stock']
            inv.low_stock_threshold = 5
            inv.save()

            # Images
            for idx, img_url in enumerate(p_item['images']):
                ProductImage.objects.update_or_create(
                    product=prod,
                    display_order=idx + 1,
                    defaults={
                        'image_url': img_url,
                        'is_primary': (idx == 0),
                        'alt_text': f"{prod.name} showcase {idx + 1}"
                    }
                )

            # Review sample
            Review.objects.get_or_create(
                product=prod,
                user=buyer_user,
                defaults={
                    'rating': 5,
                    'title': "Immaculate condition & fast vault shipping!",
                    'comment': "Came triple-bubble wrapped in factory condition. Authentic seals verified. NovaChrono is now my go-to store.",
                    'is_approved': True,
                }
            )

        self.stdout.write(self.style.SUCCESS(f"[OK] Seeded {len(products_seed)} authentic products with inventory and images."))

        # 7. Seed Sample Orders to populate Admin & History
        sample_prod1 = Product.objects.get(sku='PKMN-151-BB-JA')
        sample_prod2 = Product.objects.get(sku='ACC-BND-CHRONO-360')

        # Order 1: Confirmed
        order1_num = "NC-2026-000101"
        if not Order.objects.filter(order_number=order1_num).exists():
            order1 = Order.objects.create(
                order_number=order1_num,
                user=buyer_user,
                status=Order.Status.CONFIRMED,
                subtotal=sample_prod1.price,
                discount_amount=Decimal('0.00'),
                shipping_amount=Decimal('0.00'),
                tax_amount=round(sample_prod1.price * Decimal('0.07'), 2),
                total_amount=sample_prod1.price + round(sample_prod1.price * Decimal('0.07'), 2),
                shipping_name=address.full_name,
                shipping_phone=address.phone,
                shipping_address_line1=address.address_line1,
                shipping_address_line2=address.address_line2,
                shipping_city=address.city,
                shipping_state=address.state,
                shipping_postal_code=address.postal_code,
                shipping_country=address.country,
                billing_name=address.full_name,
                billing_address=address.address_line1,
                carrier="NovaChrono Vault Express / DHL",
                tracking_number="NC-DHL-99281034",
            )
            OrderItem.objects.create(
                order=order1,
                product=sample_prod1,
                product_name_snapshot=sample_prod1.name,
                sku_snapshot=sample_prod1.sku,
                tcg_snapshot=sample_prod1.tcg.name,
                condition_snapshot=sample_prod1.get_condition_display(),
                unit_price=sample_prod1.price,
                quantity=1,
                subtotal=sample_prod1.price,
            )
            Payment.objects.create(
                order=order1,
                payment_id=f"PAY-{order1_num}",
                amount=order1.total_amount,
                status=Payment.Status.PAID,
                transaction_reference="TXN-SAMPLE-0101",
                card_brand="Visa Platinum",
                card_last4="4242"
            )
            inv1 = Invoice.objects.create(
                invoice_number=order1_num,
                order=order1,
                due_date=date.today() + timedelta(days=7),
                subtotal=order1.subtotal,
                discount_amount=order1.discount_amount,
                shipping_amount=order1.shipping_amount,
                tax_amount=order1.tax_amount,
                grand_total=order1.total_amount,
                customer_name=order1.shipping_name,
                customer_email=buyer_user.email,
                customer_phone=order1.shipping_phone,
                shipping_address=order1.full_shipping_address,
                billing_address=order1.billing_address,
                store_name=settings_obj.store_name,
                store_address=f"{settings_obj.address_line1}, {settings_obj.city}, {settings_obj.state} {settings_obj.postal_code}",
                store_tax_id=settings_obj.tax_id,
                store_email=settings_obj.email,
                store_phone=settings_obj.phone,
            )
            InvoiceItem.objects.create(
                invoice=inv1,
                product_name=sample_prod1.name,
                sku=sample_prod1.sku,
                tcg=sample_prod1.tcg.name,
                quantity=1,
                unit_price=sample_prod1.price,
                subtotal=sample_prod1.price
            )
            OrderStatusHistory.objects.create(
                order=order1,
                previous_status=Order.Status.PENDING,
                new_status=Order.Status.CONFIRMED,
                changed_by=super_admin,
                note="Payment verified and allocation reserved in vault."
            )

        # Order 2: Delivered (historical)
        order2_num = "NC-2026-000098"
        if not Order.objects.filter(order_number=order2_num).exists():
            order2 = Order.objects.create(
                order_number=order2_num,
                user=buyer_user,
                status=Order.Status.DELIVERED,
                subtotal=sample_prod2.price,
                discount_amount=Decimal('0.00'),
                shipping_amount=Decimal('9.99'),
                tax_amount=round(sample_prod2.price * Decimal('0.07'), 2),
                total_amount=sample_prod2.price + Decimal('9.99') + round(sample_prod2.price * Decimal('0.07'), 2),
                shipping_name=address.full_name,
                shipping_phone=address.phone,
                shipping_address_line1=address.address_line1,
                shipping_city=address.city,
                shipping_state=address.state,
                shipping_postal_code=address.postal_code,
                shipping_country=address.country,
                billing_name=address.full_name,
                billing_address=address.address_line1,
                carrier="NovaChrono Vault Express / DHL",
                tracking_number="NC-DHL-88741029",
                created_at=timezone.now() - timedelta(days=5)
            )
            OrderItem.objects.create(
                order=order2,
                product=sample_prod2,
                product_name_snapshot=sample_prod2.name,
                sku_snapshot=sample_prod2.sku,
                tcg_snapshot=sample_prod2.tcg.name,
                condition_snapshot=sample_prod2.get_condition_display(),
                unit_price=sample_prod2.price,
                quantity=1,
                subtotal=sample_prod2.price,
            )
            Payment.objects.create(
                order=order2,
                payment_id=f"PAY-{order2_num}",
                amount=order2.total_amount,
                status=Payment.Status.PAID,
                transaction_reference="TXN-SAMPLE-0098",
                card_brand="Mastercard",
                card_last4="8812"
            )
            inv2 = Invoice.objects.create(
                invoice_number=order2_num,
                order=order2,
                due_date=date.today() - timedelta(days=2),
                subtotal=order2.subtotal,
                discount_amount=order2.discount_amount,
                shipping_amount=order2.shipping_amount,
                tax_amount=order2.tax_amount,
                grand_total=order2.total_amount,
                customer_name=order2.shipping_name,
                customer_email=buyer_user.email,
                customer_phone=order2.shipping_phone,
                shipping_address=order2.full_shipping_address,
                billing_address=order2.billing_address,
                store_name=settings_obj.store_name,
                store_address=f"{settings_obj.address_line1}, {settings_obj.city}, {settings_obj.state} {settings_obj.postal_code}",
                store_tax_id=settings_obj.tax_id,
                store_email=settings_obj.email,
                store_phone=settings_obj.phone,
                created_at=timezone.now() - timedelta(days=5)
            )
            InvoiceItem.objects.create(
                invoice=inv2,
                product_name=sample_prod2.name,
                sku=sample_prod2.sku,
                tcg=sample_prod2.tcg.name,
                quantity=1,
                unit_price=sample_prod2.price,
                subtotal=sample_prod2.price
            )
            OrderStatusHistory.objects.create(
                order=order2,
                previous_status=Order.Status.SHIPPED,
                new_status=Order.Status.DELIVERED,
                changed_by=staff_user,
                note="Package safely delivered and signed by customer."
            )

        self.stdout.write(self.style.SUCCESS("[OK] Seeded sample orders, payments, invoices, and status history."))
        self.stdout.write(self.style.SUCCESS("[OK] NovaChrono seed complete! Ready to launch."))
