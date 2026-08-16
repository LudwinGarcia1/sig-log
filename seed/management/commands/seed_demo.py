"""Generate a reproducible 18-month operation with learnable patterns."""

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker

from apps.customers.models import Customer
from apps.deliveries.models import DelayCause, Delivery
from apps.fuel.models import FuelLoad
from apps.maintenance.models import Maintenance
from apps.operators.models import Operator
from apps.routes.models import Route
from apps.vehicles.models import Vehicle
from seed.patterns import (
    BASE_EFFICIENCY,
    DELAY_CAUSE_WEIGHTS,
    PEAK_HOURS,
    ROUTE_ARCHETYPES,
    delay_probability,
)

BRANDS = [
    ("Freightliner", "Cascadia", "TRUCK"),
    ("Kenworth", "T680", "TRUCK"),
    ("International", "ProStar", "TRAILER"),
    ("Volvo", "VNL", "TRAILER"),
    ("Mercedes-Benz", "Sprinter", "VAN"),
    ("Ford", "Transit", "VAN"),
    ("Nissan", "NP300", "PICKUP"),
    ("Chevrolet", "Silverado", "PICKUP"),
]
CAPACITY = {
    "TRUCK": (9000, 14000),
    "TRAILER": (18000, 28000),
    "VAN": (900, 1800),
    "PICKUP": (700, 1200),
}
TANK = {"TRUCK": 300, "TRAILER": 450, "VAN": 80, "PICKUP": 90}
STATES = ["México", "Ciudad de México", "Querétaro", "Guanajuato", "Puebla",
          "Hidalgo", "Jalisco", "Nuevo León", "Veracruz", "Morelos"]
WORKSHOPS = ["Taller Central", "Servicio Diésel del Bajío", "Mecánica Integral Toluca",
             "Refaccionaria y Taller Norte", "Centro de Servicio Kenworth"]


class Command(BaseCommand):
    help = "Genera datos sintéticos de operación logística con patrones sembrados."

    def add_arguments(self, parser):
        parser.add_argument("--months", type=int, default=18)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--dirty-rate", type=float, default=0.03)

    @transaction.atomic
    def handle(self, *args, **options):
        months = options["months"]
        self.rng = random.Random(options["seed"])
        self.fake = Faker("es_MX")
        Faker.seed(options["seed"])
        self.verbose = options["verbosity"] > 0

        self._reset()
        self.end_date = date.today().replace(day=1) - timedelta(days=1)
        self.start_date = (self.end_date - timedelta(days=30 * months)).replace(day=1)

        customers = self._create_customers()
        operators = self._create_operators()
        routes = self._create_routes()
        vehicles = self._create_vehicles()
        self._create_deliveries(customers, routes, vehicles, operators)
        self._create_fuel_loads(vehicles, operators)
        self._create_maintenance(vehicles)
        self._inject_dirty_records(options["dirty_rate"])

        if self.verbose:
            self.stdout.write(self.style.SUCCESS(
                f"Sembrado completo: {len(customers)} clientes, {len(vehicles)} vehículos, "
                f"{len(operators)} operadores, {len(routes)} rutas, "
                f"{Delivery.objects.count()} entregas, {FuelLoad.objects.count()} cargas, "
                f"{Maintenance.objects.count()} mantenimientos."
            ))

    # ------------------------------------------------------------------ setup

    def _reset(self):
        FuelLoad.objects.all().delete()
        Maintenance.objects.all().delete()
        Delivery.objects.all().delete()
        Customer.objects.all().delete()
        Vehicle.objects.all().delete()
        Operator.objects.all().delete()
        Route.objects.all().delete()
        if not DelayCause.objects.exists():
            raise SystemExit(
                "Falta el catálogo de causas: ejecuta 'python manage.py loaddata delay_causes'."
            )

    def _aware(self, day, hour, minute=0):
        return timezone.make_aware(datetime.combine(day, time(hour, minute)))

    # ------------------------------------------------------------- catalogues

    def _create_customers(self):
        rows = []
        for index in range(1, 121):
            # Premium customers are 20% of the base and drive most of the volume.
            if index <= 24:
                customer_type = "PREMIUM"
            elif index <= 84:
                customer_type = "REGULAR"
            else:
                customer_type = "OCCASIONAL"
            rows.append(Customer(
                code=f"CLI-{index:04d}",
                business_name=self.fake.company(),
                tax_id=self.fake.bothify("???######???").upper(),
                contact_name=self.fake.name(),
                phone=self.fake.numerify("##########"),
                email=self.fake.company_email(),
                address=self.fake.street_address(),
                city=self.fake.city(),
                state=self.rng.choice(STATES),
                postal_code=self.fake.numerify("#####"),
                customer_type=customer_type,
            ))
        return Customer.objects.bulk_create(rows)

    def _create_operators(self):
        rows = []
        for index in range(1, 41):
            hired = self.fake.date_between(start_date="-12y", end_date="-3m")
            rows.append(Operator(
                employee_number=f"OP-{index:04d}",
                first_name=self.fake.first_name(),
                last_name=self.fake.last_name(),
                license_number=self.fake.bothify("LF-#####"),
                license_type=self.rng.choice(["B", "C", "C", "C", "E"]),
                license_expiry=self.fake.date_between(start_date="+1m", end_date="+4y"),
                hire_date=hired,
                phone=self.fake.numerify("##########"),
                status="ACTIVE" if index % 13 else "VACATION",
            ))
        return Operator.objects.bulk_create(rows)

    def _create_routes(self):
        rows = []
        index = 0
        self.route_profiles = {}
        for archetype in ROUTE_ARCHETYPES:
            for _ in range(archetype["count"]):
                index += 1
                code = f"RUT-{index:03d}"
                distance = Decimal(self.rng.randint(*archetype["distance_km"]))
                speed = self.rng.randint(*archetype["speed_kmh"])
                duration = int((distance / Decimal(speed)) * 60)
                zone = self.rng.choice(archetype["zones"])
                origin = self.fake.city()
                destination = self.fake.city()
                rows.append(Route(
                    code=code,
                    name=f"{origin} — {destination}",
                    origin_city=origin,
                    destination_city=destination,
                    distance_km=distance,
                    estimated_duration_min=duration,
                    route_type=archetype["route_type"],
                    zone=zone,
                    toll_cost=Decimal(self.rng.randint(0, 40) * 15),
                ))
                self.route_profiles[code] = {
                    "archetype": archetype,
                    "monthly_volume": self.rng.randint(*archetype["monthly_volume"]),
                    "cargo_kg": archetype["cargo_kg"],
                }
        return Route.objects.bulk_create(rows)

    def _create_vehicles(self):
        rows = []
        current_year = date.today().year
        for index in range(1, 51):
            brand, model, vehicle_type = BRANDS[index % len(BRANDS)]
            # A third of the fleet is deliberately old: worse fuel, more failures.
            age = self.rng.randint(9, 15) if index % 3 == 0 else self.rng.randint(0, 8)
            odometer = Decimal(self.rng.randint(40_000, 90_000) + age * 22_000)
            low, high = CAPACITY[vehicle_type]
            rows.append(Vehicle(
                plate=f"{self.fake.lexify('???').upper()}{index:04d}",
                economic_number=f"EC-{index:04d}",
                brand=brand,
                model=model,
                year=current_year - age,
                vehicle_type=vehicle_type,
                cargo_capacity_kg=Decimal(self.rng.randint(low, high)),
                fuel_type="DIESEL" if vehicle_type in ("TRUCK", "TRAILER") else "GASOLINE",
                tank_capacity_l=Decimal(TANK[vehicle_type]),
                current_odometer_km=odometer,
                acquisition_date=date(current_year - age, self.rng.randint(1, 12), 15),
                next_service_km=odometer + Decimal(self.rng.randint(500, 9000)),
                last_service_date=date.today() - timedelta(days=self.rng.randint(5, 210)),
                status="AVAILABLE",
            ))
        return Vehicle.objects.bulk_create(rows)

    # ------------------------------------------------------------ transactions

    def _weighted_cause(self):
        codes = [code for code, _ in DELAY_CAUSE_WEIGHTS]
        weights = [weight for _, weight in DELAY_CAUSE_WEIGHTS]
        return self.rng.choices(codes, weights=weights, k=1)[0]

    def _create_deliveries(self, customers, routes, vehicles, operators):
        causes = {cause.code: cause for cause in DelayCause.objects.all()}
        premium = [c for c in customers if c.customer_type == "PREMIUM"]
        regular = [c for c in customers if c.customer_type != "PREMIUM"]

        batch, folio = [], 0
        day = self.start_date
        while day <= self.end_date:
            if day.weekday() == 6:                       # no Sunday operation
                day += timedelta(days=1)
                continue
            for route in routes:
                profile = self.route_profiles[route.code]
                daily_chance = profile["monthly_volume"] / 26
                shipments = int(daily_chance) + (
                    1 if self.rng.random() < (daily_chance % 1) else 0
                )
                for _ in range(shipments):
                    folio += 1
                    # Peak hours carry most of the traffic.
                    hour = (
                        self.rng.choice(sorted(PEAK_HOURS))
                        if self.rng.random() < 0.55
                        else self.rng.randint(5, 21)
                    )
                    vehicle = self.rng.choice(vehicles)
                    operator = self.rng.choice(operators)
                    # Premium customers concentrate 60% of the volume.
                    customer = self.rng.choice(
                        premium if self.rng.random() < 0.60 else regular
                    )
                    departure = self._aware(day, hour, self.rng.choice([0, 15, 30, 45]))
                    planned = route.estimated_duration_min
                    scheduled_arrival = departure + timedelta(minutes=planned)

                    probability = delay_probability(
                        route.zone, route.route_type, hour,
                        day.weekday(), date.today().year - vehicle.year,
                    )
                    late = self.rng.random() < probability
                    if late:
                        extra = self.rng.randint(16, int(planned * 0.6) + 40)
                    else:
                        extra = self.rng.randint(-int(planned * 0.10) - 5, 14)

                    actual_arrival = scheduled_arrival + timedelta(minutes=extra)
                    is_late = extra > 15
                    low, high = profile["cargo_kg"]
                    weight = Decimal(self.rng.randint(low, high))

                    batch.append(Delivery(
                        folio=f"ENT-{day.year}-{folio:05d}",
                        customer=customer,
                        route=route,
                        vehicle=vehicle,
                        operator=operator,
                        delay_cause=causes[self._weighted_cause()] if is_late else None,
                        scheduled_departure=departure,
                        actual_departure=departure + timedelta(
                            minutes=self.rng.randint(0, 12)
                        ),
                        scheduled_arrival=scheduled_arrival,
                        actual_arrival=actual_arrival,
                        cargo_weight_kg=min(weight, vehicle.cargo_capacity_kg),
                        packages_count=self.rng.randint(1, 120),
                        declared_value=weight * Decimal(self.rng.randint(20, 90)),
                        freight_cost=(
                            route.distance_km * Decimal("18.5") + route.toll_cost
                        ).quantize(Decimal("0.01")),
                        status="DELAYED" if is_late else "DELIVERED",
                    ))
                    if len(batch) >= 2000:
                        Delivery.objects.bulk_create(batch)
                        batch = []
            day += timedelta(days=1)

        if batch:
            Delivery.objects.bulk_create(batch)

        # A small open tail, so the system shows live operation too.
        open_ones = list(Delivery.objects.order_by("-scheduled_departure")[:60])
        for index, delivery in enumerate(open_ones):
            delivery.actual_arrival = None
            delivery.delay_cause = None
            delivery.status = "IN_TRANSIT" if index % 2 else "SCHEDULED"
        Delivery.objects.bulk_update(
            open_ones, ["actual_arrival", "delay_cause", "status"]
        )

        return Delivery.objects.count()

    def _create_fuel_loads(self, vehicles, operators):
        rows, folio = [], 0
        for vehicle in vehicles:
            odometer = vehicle.current_odometer_km - Decimal(
                self.rng.randint(25_000, 45_000)
            )
            age = date.today().year - vehicle.year
            # Old units burn measurably more fuel.
            penalty = Decimal("0.78") if age > 8 else Decimal("1.00")
            efficiency = BASE_EFFICIENCY[vehicle.vehicle_type] * penalty
            moment = self._aware(self.start_date, 8)
            while moment.date() <= self.end_date:
                folio += 1
                litres = Decimal(self.rng.randint(
                    int(vehicle.tank_capacity_l * Decimal("0.5")),
                    int(vehicle.tank_capacity_l),
                ))
                travelled = (
                    litres * efficiency * Decimal(str(self.rng.uniform(0.92, 1.08)))
                ).quantize(Decimal("0.01"))
                odometer += travelled
                rows.append(FuelLoad(
                    folio=f"COM-{folio:06d}",
                    vehicle=vehicle,
                    operator=self.rng.choice(operators),
                    load_datetime=moment,
                    station_name=f"Pemex {self.fake.city()}",
                    liters=litres,
                    price_per_liter=Decimal(str(round(self.rng.uniform(23.0, 27.5), 2))),
                    total_cost=Decimal("0.00"),
                    odometer_km=odometer,
                ))
                moment += timedelta(days=self.rng.randint(4, 11))
        for row in rows:
            row.total_cost = (row.liters * row.price_per_liter).quantize(Decimal("0.01"))
        FuelLoad.objects.bulk_create(rows, batch_size=2000)

    def _create_maintenance(self, vehicles):
        rows, folio = [], 0
        for vehicle in vehicles:
            age = date.today().year - vehicle.year
            # Old units fail more often: this is the pattern behind "mayores costos".
            services = self.rng.randint(14, 26) if age > 8 else self.rng.randint(6, 14)
            odometer = vehicle.current_odometer_km - Decimal(
                self.rng.randint(30_000, 60_000)
            )
            day = self.start_date
            for _ in range(services):
                folio += 1
                day += timedelta(days=self.rng.randint(18, 55))
                if day > self.end_date:
                    break
                odometer += Decimal(self.rng.randint(4_000, 11_000))
                corrective = self.rng.random() < (0.55 if age > 8 else 0.25)
                labor = Decimal(self.rng.randint(800, 6500) if corrective
                                else self.rng.randint(600, 2200))
                parts = Decimal(self.rng.randint(1500, 28000) if corrective
                                else self.rng.randint(800, 5200))
                rows.append(Maintenance(
                    folio=f"MTO-{folio:06d}",
                    vehicle=vehicle,
                    maintenance_type="CORRECTIVE" if corrective else "PREVENTIVE",
                    service_date=day,
                    odometer_km=odometer,
                    description=self.rng.choice([
                        "Cambio de aceite y filtros", "Ajuste de frenos",
                        "Reemplazo de balatas", "Reparación de sistema eléctrico",
                        "Cambio de llantas", "Servicio de suspensión",
                        "Reparación de transmisión", "Afinación mayor",
                    ]),
                    workshop=self.rng.choice(WORKSHOPS),
                    labor_cost=labor,
                    parts_cost=parts,
                    total_cost=labor + parts,
                    next_service_km=odometer + Decimal("10000.00"),
                    days_out_of_service=self.rng.randint(1, 6) if corrective else 1,
                    status="COMPLETED",
                ))
        Maintenance.objects.bulk_create(rows, batch_size=2000)

    # ------------------------------------------------------------------ dirt

    def _inject_dirty_records(self, dirty_rate):
        """Plant the defects the ETL cleaning rules are meant to catch.

        Written with queryset.update() so model-level validation is bypassed —
        which is exactly how bad data arrives from a real source system.
        """
        total = Delivery.objects.count()
        sample = max(int(total * dirty_rate), 12)

        # 1. Arrival before departure.
        broken = list(
            Delivery.objects.filter(actual_arrival__isnull=False)
            .order_by("folio")
            .values_list("id", flat=True)[: sample // 3]
        )
        for delivery in Delivery.objects.filter(id__in=broken):
            Delivery.objects.filter(id=delivery.id).update(
                actual_arrival=delivery.actual_departure - timedelta(minutes=30)
            )

        # 2. Untrimmed, lower-case city names on customers.
        for customer in Customer.objects.order_by("code")[:15]:
            Customer.objects.filter(id=customer.id).update(
                city=f"  {customer.city.lower()}  ",
                tax_id=customer.tax_id.lower(),
            )

        # 3. Blank city — must become DESCONOCIDA.
        Customer.objects.filter(
            id__in=list(
                Customer.objects.order_by("-code").values_list("id", flat=True)[:8]
            )
        ).update(city="")

        # 4. Duplicate tax ids across two customer codes.
        first, second = Customer.objects.order_by("code")[:2]
        Customer.objects.filter(id=second.id).update(tax_id=first.tax_id)

        # 5. Zero-litre and outlier fuel loads.
        zeroed = list(
            FuelLoad.objects.order_by("folio").values_list("id", flat=True)[:10]
        )
        FuelLoad.objects.filter(id__in=zeroed).update(
            liters=Decimal("0.00"), total_cost=Decimal("0.00")
        )
        outliers = list(
            FuelLoad.objects.order_by("-folio").values_list("id", flat=True)[:10]
        )
        FuelLoad.objects.filter(id__in=outliers).update(liters=Decimal("1.00"))

        # 6. Negative freight cost.
        Delivery.objects.filter(
            id__in=list(
                Delivery.objects.order_by("-folio").values_list("id", flat=True)[:8]
            )
        ).update(freight_cost=Decimal("-1.00"))
