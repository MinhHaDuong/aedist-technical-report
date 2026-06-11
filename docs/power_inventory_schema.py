"""
AEDIST — Schéma d'inventaire de centrales thermiques.

Modèle à trois niveaux :  Site (complexe) ⊃ Plant (centrale) ⊃ Unit (tranche)
avec un niveau intermédiaire optionnel Block (train CCGT, entité de dispatch).

Principes :
  - La TRANCHE (Unit) est l'objet atomique : elle porte la sémantique du dispatch
    (coût marginal, Pmin, démarrage, rampe).
  - La capacité d'une centrale/site est DÉRIVÉE (somme des tranches), jamais saisie
    comme source de vérité. La valeur extraite de la source est conservée à part
    (`declared_capacity_mw`) pour réconciliation.
  - Validation DOUCE : les incohérences sont signalées (warnings), pas rejetées.
    Seules les violations structurelles dures lèvent une erreur.

Python 3.11+, Pydantic v2.  Standard, sans dépendance propriétaire.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, computed_field, model_validator

# Tailles de tranche « catalogue » par époque/techno (MW). Sert d'heuristique
# de plausibilité, pas de contrainte dure.
STANDARD_UNIT_SIZES_MW: tuple[float, ...] = (110, 300, 330, 600, 622, 660, 750, 1000, 1240, 1350)
CAPACITY_TOLERANCE: float = 1.0  # MW : écart toléré déclaré vs dérivé


class Fuel(StrEnum):
    COAL = "coal"
    LNG = "lng"                # GN importé liquéfié
    NATURAL_GAS = "natural_gas"  # GN domestique
    OIL = "oil"
    BIOMASS = "biomass"
    AMMONIA = "ammonia"
    HYDROGEN = "hydrogen"


class Technology(StrEnum):
    SUBCRITICAL = "subcritical"
    SUPERCRITICAL = "supercritical"
    ULTRA_SUPERCRITICAL = "ultra_supercritical"
    CFB = "cfb"          # lit fluidisé circulant
    CCGT = "ccgt"        # cycle combiné
    OCGT = "ocgt"        # turbine à gaz simple cycle
    STEAM = "steam"      # cycle vapeur, criticité non précisée


class Status(StrEnum):
    """Aligné sur la nomenclature Global Energy Monitor."""
    OPERATING = "operating"
    CONSTRUCTION = "construction"
    PERMITTED = "permitted"
    ANNOUNCED = "announced"
    PRE_PERMIT = "pre_permit"
    SHELVED = "shelved"          # dormant (cf. Vĩnh Tân 3)
    CANCELLED = "cancelled"
    MOTHBALLED = "mothballed"
    RETIRED = "retired"


def _is_decomposable(total: float, sizes: tuple[float, ...] = STANDARD_UNIT_SIZES_MW,
                     tol: float = 5.0) -> bool:
    """Le total se décompose-t-il en k tranches d'une taille standard unique ?"""
    for s in sizes:
        k = round(total / s)
        if k >= 1 and abs(k * s - total) <= tol:
            return True
    return False


class Unit(BaseModel):
    """Tranche / tổ máy : groupe turbo-alternateur. Entité atomique du dispatch."""
    unit_id: str
    name: str | None = None
    capacity_mw: float = Field(gt=0, description="Puissance nominale (nameplate)")
    fuel: Fuel
    technology: Technology
    status: Status
    cod: date | None = Field(default=None, description="Commercial Operation Date")
    pmin_mw: float | None = Field(default=None, ge=0, description="Puissance minimale stable")
    heat_rate_kj_per_kwh: float | None = Field(default=None, gt=0)
    ramp_rate_mw_per_min: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _check_pmin(self) -> Unit:
        if self.pmin_mw is not None and self.pmin_mw > self.capacity_mw:
            raise ValueError(f"{self.unit_id}: pmin_mw ({self.pmin_mw}) > capacity_mw ({self.capacity_mw})")
        return self


class Block(BaseModel):
    """Train CCGT : regroupe les tranches dispatchées ensemble (ex. config 2x1).

    Pour un cycle combiné, l'entité de dispatch est le bloc, pas la turbomachine
    isolée : la turbine vapeur dépend des turbines à gaz.
    """
    block_id: str
    configuration: str | None = Field(default=None, description="ex. '2x1' = 2 TAG + 1 TAV")
    unit_ids: list[str] = Field(default_factory=list)
    is_dispatch_entity: bool = True


class Plant(BaseModel):
    """Centrale / projet : conteneur de tranches. Capacité = somme dérivée."""
    plant_id: str
    name: str
    operator: str | None = None
    country: str | None = None
    province: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    grid_connection_kv: float | None = Field(default=None, gt=0)
    units: list[Unit] = Field(default_factory=list)
    blocks: list[Block] = Field(default_factory=list)
    declared_capacity_mw: float | None = Field(
        default=None, gt=0, description="Capacité telle qu'extraite de la source"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def capacity_mw(self) -> float:
        """Capacité dérivée = Σ tranches."""
        return sum(u.capacity_mw for u in self.units)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def n_units(self) -> int:
        return len(self.units)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def operating_capacity_mw(self) -> float:
        """Capacité réellement en exploitation (exclut planned/cancelled/shelved...)."""
        return sum(u.capacity_mw for u in self.units if u.status == Status.OPERATING)

    @model_validator(mode="after")
    def _check_block_references(self) -> Plant:
        known = {u.unit_id for u in self.units}
        for b in self.blocks:
            unknown = set(b.unit_ids) - known
            if unknown:
                raise ValueError(f"{self.plant_id}: bloc {b.block_id} référence des tranches inconnues {unknown}")
        return self

    def consistency_warnings(self) -> list[str]:
        """Validation douce : signale sans rejeter. À router vers curation humaine."""
        w: list[str] = []

        # 1. Réconciliation déclaré vs dérivé
        if self.declared_capacity_mw is not None and self.units:
            gap = abs(self.declared_capacity_mw - self.capacity_mw)
            if gap > CAPACITY_TOLERANCE:
                w.append(
                    f"Capacité déclarée {self.declared_capacity_mw} MW ≠ Σ tranches "
                    f"{self.capacity_mw} MW (écart {gap} MW) — vérifier tranche/centrale/complexe."
                )

        # 2. Total déclaré non décomposable en tailles standard (pas de tranches saisies)
        if not self.units and self.declared_capacity_mw is not None:
            if not _is_decomposable(self.declared_capacity_mw):
                w.append(
                    f"Capacité {self.declared_capacity_mw} MW non décomposable en tailles "
                    f"standard — possible total de complexe, pas de centrale."
                )

        # 3. Tranches CCGT hors de tout bloc
        ccgt_units = {u.unit_id for u in self.units if u.technology == Technology.CCGT}
        in_blocks = {uid for b in self.blocks for uid in b.unit_ids}
        orphan = ccgt_units - in_blocks
        if orphan:
            w.append(f"Tranches CCGT sans bloc de dispatch : {orphan}.")

        # 4. Cas impair (signal, pas erreur)
        if self.n_units % 2 == 1 and self.n_units > 1:
            w.append(f"Nombre impair de tranches ({self.n_units}) — phase ajoutée ou redimensionnement (ex. Vĩnh Tân 3).")

        return w


class Site(BaseModel):
    """Complexe : regroupe plusieurs centrales sur un même site (ex. Vĩnh Tân)."""
    site_id: str
    name: str
    country: str | None = None
    province: str | None = None
    plants: list[Plant] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def capacity_mw(self) -> float:
        return sum(p.capacity_mw for p in self.plants)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def operating_capacity_mw(self) -> float:
        return sum(p.operating_capacity_mw for p in self.plants)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def n_units(self) -> int:
        return sum(p.n_units for p in self.plants)

    def consistency_warnings(self) -> list[str]:
        out: list[str] = []
        for p in self.plants:
            out.extend(f"[{p.plant_id}] {msg}" for msg in p.consistency_warnings())
        return out


if __name__ == "__main__":
    # Exemple : complexe Vĩnh Tân, centrale 3 (cas impair, projet dormant)
    vt3 = Plant(
        plant_id="vinh-tan-3",
        name="Vĩnh Tân 3",
        operator="OneEnergy/EVN/Pacific",
        country="VN", province="Bình Thuận",
        declared_capacity_mw=1980,
        units=[
            Unit(unit_id=f"vt3-{i}", capacity_mw=660, fuel=Fuel.COAL,
                 technology=Technology.SUPERCRITICAL, status=Status.SHELVED)
            for i in (1, 2, 3)
        ],
    )
    print(f"Vĩnh Tân 3 : {vt3.n_units} tranches, {vt3.capacity_mw} MW "
          f"(opérationnel : {vt3.operating_capacity_mw} MW)")
    for msg in vt3.consistency_warnings():
        print("  ⚠", msg)
