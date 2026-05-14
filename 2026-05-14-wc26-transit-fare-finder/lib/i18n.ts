export type Lang = "en" | "es" | "pt";

export const LANGS: { id: Lang; label: string; flag: string }[] = [
  { id: "en", label: "English", flag: "EN" },
  { id: "es", label: "Español", flag: "ES" },
  { id: "pt", label: "Português", flag: "PT" },
];

type Dict = Record<string, string>;

const en: Dict = {
  brand: "WC26 Fare Finder",
  tagline: "Match-day transit for the New York / New Jersey World Cup venues.",
  pickOrigin: "Pick origin",
  pickMatch: "Pick match",
  cheapestFirst: "Ranked cheapest first",
  optionsHeading: "Your options to MetLife",
  price: "Price",
  doorTime: "Door-to-door",
  transfers: "Transfers",
  minutes: "min",
  addToCalendar: "Add departure to calendar",
  lastReturnWarn: "Late finish — confirm last return",
  reliability: "Reliability",
  high: "high",
  medium: "medium",
  low: "low",
  faq: "Fan FAQ",
  faqQ1: "Why are the fares cheaper now?",
  faqA1:
    "On May 14, 2026, NY and NJ governors announced that the NJ Transit match-day train ticket drops to $98 from $150 round-trip, and the official fan shuttle drops to $20 from $80 round-trip.",
  faqQ2: "Are these prices included with my match ticket?",
  faqA2:
    "Not yet. The new prices apply when you buy through NJ Transit or the official shuttle operator. Bring your match ticket as proof of travel.",
  faqQ3: "What if my match ends late?",
  faqA3:
    "Trains and shuttles run extended service on match days, but late kickoffs can still mean tight last-train windows. We flag any match ending after 22:00 on each option card.",
  faqQ4: "Can I drive and park?",
  faqA4:
    "Yes but expect heavy queuing and a $80+ match-day parking pass. Transit is faster end-to-end for most fans.",
  newsSource: "Fare-cut announcement",
  publishedOn: "Published",
  footerNote:
    "Stub fixture data. Not affiliated with FIFA, NJ Transit, or any team. Confirm fares before travel.",
  resultsFor: "Results for",
  on: "on",
  selectBoth: "Pick an origin and a match to see options.",
  savedVs: "Saved vs original",
  reliable: "Reliability",
  legend: "Lower price = better. Sort is automatic.",
};

const es: Dict = {
  brand: "WC26 Buscador de Tarifas",
  tagline: "Transporte el día del partido para las sedes del Mundial en NY / NJ.",
  pickOrigin: "Elegir origen",
  pickMatch: "Elegir partido",
  cheapestFirst: "Ordenado de más barato",
  optionsHeading: "Opciones hasta MetLife",
  price: "Precio",
  doorTime: "Puerta a puerta",
  transfers: "Trasbordos",
  minutes: "min",
  addToCalendar: "Añadir salida al calendario",
  lastReturnWarn: "Final tardío — confirma el último regreso",
  reliability: "Fiabilidad",
  high: "alta",
  medium: "media",
  low: "baja",
  faq: "FAQ para aficionados",
  faqQ1: "¿Por qué bajaron los precios?",
  faqA1:
    "El 14 de mayo de 2026, los gobernadores de NY y NJ anunciaron que el tren NJ Transit del día del partido baja a 98 USD desde 150 USD ida y vuelta, y el bus oficial baja a 20 USD desde 80 USD ida y vuelta.",
  faqQ2: "¿Están incluidos en mi entrada?",
  faqA2:
    "Todavía no. Los nuevos precios aplican al comprar por NJ Transit o el operador oficial del bus. Lleva la entrada como prueba.",
  faqQ3: "¿Y si el partido termina tarde?",
  faqA3:
    "Los trenes y buses tienen servicio extendido, pero los partidos nocturnos pueden dejar poco margen para el último tren. Marcamos cualquier partido que termine después de las 22:00.",
  faqQ4: "¿Puedo conducir y aparcar?",
  faqA4:
    "Sí, pero habrá largas colas y un pase de aparcamiento de más de 80 USD. El transporte público suele ser más rápido.",
  newsSource: "Anuncio de la rebaja de tarifas",
  publishedOn: "Publicado",
  footerNote:
    "Datos de partidos de prueba. Sin afiliación con FIFA, NJ Transit ni equipos. Verifica antes de viajar.",
  resultsFor: "Resultados para",
  on: "el",
  selectBoth: "Elige un origen y un partido para ver las opciones.",
  savedVs: "Ahorro frente al original",
  reliable: "Fiabilidad",
  legend: "Menor precio = mejor. Orden automático.",
};

const pt: Dict = {
  brand: "WC26 Comparador de Tarifas",
  tagline: "Transporte no dia do jogo para as sedes da Copa em NY / NJ.",
  pickOrigin: "Escolher origem",
  pickMatch: "Escolher jogo",
  cheapestFirst: "Do mais barato ao mais caro",
  optionsHeading: "Opções até o MetLife",
  price: "Preço",
  doorTime: "Porta a porta",
  transfers: "Baldeações",
  minutes: "min",
  addToCalendar: "Adicionar saída à agenda",
  lastReturnWarn: "Término tarde — confirme o último retorno",
  reliability: "Confiabilidade",
  high: "alta",
  medium: "média",
  low: "baixa",
  faq: "FAQ do torcedor",
  faqQ1: "Por que as tarifas caíram?",
  faqA1:
    "Em 14 de maio de 2026, os governadores de NY e NJ anunciaram que o trem NJ Transit no dia do jogo cai para US$98 (de US$150) ida e volta, e o ônibus oficial cai para US$20 (de US$80) ida e volta.",
  faqQ2: "Está incluso no meu ingresso?",
  faqA2:
    "Ainda não. Os novos preços valem ao comprar pela NJ Transit ou pela operadora oficial do ônibus. Leve seu ingresso como comprovante.",
  faqQ3: "E se o jogo terminar tarde?",
  faqA3:
    "Há serviço estendido nos dias de jogo, mas partidas noturnas podem ter janelas curtas para o último trem. Marcamos qualquer jogo que termine após 22h.",
  faqQ4: "Posso dirigir e estacionar?",
  faqA4:
    "Sim, mas espere filas e passe de estacionamento acima de US$80 no dia do jogo. O transporte público costuma ser mais rápido.",
  newsSource: "Anúncio da redução das tarifas",
  publishedOn: "Publicado",
  footerNote:
    "Dados de jogos fictícios. Sem afiliação com FIFA, NJ Transit ou clubes. Confirme antes de viajar.",
  resultsFor: "Resultados para",
  on: "em",
  selectBoth: "Escolha origem e jogo para ver as opções.",
  savedVs: "Economia versus original",
  reliable: "Confiabilidade",
  legend: "Menor preço = melhor. Ordenado automaticamente.",
};

export const STRINGS: Record<Lang, Dict> = { en, es, pt };

export const t = (lang: Lang, key: string): string =>
  STRINGS[lang]?.[key] ?? STRINGS.en[key] ?? key;
