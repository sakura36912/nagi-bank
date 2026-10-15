export interface WeaponDefinition {
  id: string;
  name: string;
  skill: string;
  skillDescription: string;
}

export const WEAPONS: WeaponDefinition[] = [
  {
    id: "greatsword",
    name: "大剣",
    skill: "斬鉄撃",
    skillDescription: "重い一撃で敵を打ち砕く。",
  },
  {
    id: "sword",
    name: "片手剣",
    skill: "連閃",
    skillDescription: "隙を逃さず素早く斬り返す。",
  },
  {
    id: "spear",
    name: "槍",
    skill: "貫通突き",
    skillDescription: "間合いの外から一直線に突く。",
  },
  {
    id: "bow",
    name: "弓",
    skill: "弱点狙撃",
    skillDescription: "敵の急所を正確に射抜く。",
  },
  {
    id: "dual-blades",
    name: "双剣",
    skill: "疾風連斬",
    skillDescription: "身軽な連続攻撃で畳みかける。",
  },
  {
    id: "staff",
    name: "杖",
    skill: "魔力解放",
    skillDescription: "内なる魔力を解き放つ。",
  },
];

export function findWeapon(id: string | null | undefined): WeaponDefinition | undefined {
  return WEAPONS.find((weapon) => weapon.id === id);
}
