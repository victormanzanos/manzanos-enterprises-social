#!/usr/bin/env python3
"""Manzanos Enterprises — Instagram content (single source of truth).

Two content pools, exactly what Victor asked for:

  QUOTES — the 80 entrepreneurial motivation phrases from the corporate
           section of manzanosenterprises.com (/rsc · "Words That Drive Us").
           Each is (es, en): the card shows the Spanish line, the caption
           carries both languages. Index-aligned with the website arrays.

  BLOG   — highlights of real articles on manzanosenterprises.com/news.
           The card promotes the article (title + hook), caption sends to
           the link in bio. Seeded from the live blog; add more freely.

WHY one module: both make_me.py (image generation) and daily_engine.py
(publishing) import from here, so captions and cards never drift.
"""

# ──────────────────────────────────────────────────────────────────────────
# 80 motivation quotes — (Spanish, English), index-aligned with the website.
# Source: src/app/[locale]/rsc/page.tsx (quotesEs / quotesEn).
# ──────────────────────────────────────────────────────────────────────────
QUOTES = [
    ("Nadie quiere fracasar, por eso la mayoría nunca lo intenta.",
     "Nobody wants to fail, which is why most people never even try."),
    ("Las grandes empresas siempre comienzan con una decisión valiente.",
     "Great companies always start with a brave decision."),
    ("Emprender no es evitar el riesgo, es crear oportunidades.",
     "Entrepreneurship is not about avoiding risk, it is about creating opportunity."),
    ("Construir empresas es una de las formas más poderosas de crear un futuro mejor.",
     "Building companies is one of the most powerful ways to create a better future."),
    ("Un negocio sin alma es solo una transacción esperando su fin.",
     "A business without a soul is just a transaction waiting to end."),
    ("El mundo no premia a quienes esperan permiso.",
     "The world does not reward those who wait for permission."),
    ("Si tu visión no te asusta un poco, no es lo suficientemente grande.",
     "If your vision does not scare you a little, it is not big enough."),
    ("El coraje es la primera inversión que todo emprendedor debe hacer.",
     "Courage is the first investment every entrepreneur must make."),
    ("La comodidad es el enemigo de toda gran empresa.",
     "Comfort is the enemy of every great enterprise."),
    ("El mejor momento para empezar fue ayer. El segundo mejor es ahora mismo.",
     "The best time to start was yesterday. The second best time is right now."),
    ("Las fronteras son líneas en un mapa, no límites a la ambición.",
     "Borders are lines on a map, not limits on ambition."),
    ("Una buena idea no vale nada sin el valor de ejecutarla.",
     "A good idea is worthless without the nerve to execute it."),
    ("El legado no se hereda. Se construye, ladrillo a ladrillo, generación tras generación.",
     "Legacy is not inherited. It is built, brick by brick, generation after generation."),
    ("Los mercados premian a quienes resuelven problemas que otros eligen ignorar.",
     "Markets reward those who solve problems others choose to ignore."),
    ("El beneficio es consecuencia del valor creado, nunca al revés.",
     "Profit is a consequence of value created, never the other way around."),
    ("Piensa en décadas, actúa en días.",
     "Think in decades, act in days."),
    ("Toda industria fue alguna vez transformada por alguien que se negó a aceptar el statu quo.",
     "Every industry was once disrupted by someone who refused to accept the status quo."),
    ("El emprendedor que teme al fracaso ya se ha rendido ante él.",
     "The entrepreneur who fears failure has already surrendered to it."),
    ("Pensar internacionalmente no es una estrategia. Es una habilidad de supervivencia.",
     "International thinking is not a strategy. It is a survival skill."),
    ("Contrata personas que te desafíen, no personas que te hagan eco.",
     "Hire people who challenge you, not people who echo you."),
    ("La cultura de una empresa es la sombra que proyecta su fundador.",
     "A company's culture is the shadow its founder casts."),
    ("Velocidad sin dirección es solo caos costoso.",
     "Speed without direction is just expensive chaos."),
    ("La sostenibilidad no es filantropía. Es negocio inteligente a largo plazo.",
     "Sustainability is not philanthropy. It is intelligent long-term business."),
    ("Tu competencia no es el enemigo. La complacencia sí lo es.",
     "Your competition is not the enemy. Complacency is."),
    ("Los verdaderos líderes construyen organizaciones que prosperan sin ellos.",
     "Real leaders build organizations that thrive without them."),
    ("La diferencia entre un soñador y un fundador es un contrato firmado.",
     "The difference between a dreamer and a founder is a signed contract."),
    ("La diversificación no es una cobertura contra el fracaso. Es un compromiso con el crecimiento.",
     "Diversification is not a hedge against failure. It is a commitment to growth."),
    ("Cuando todos van en una dirección, la oportunidad está en la contraria.",
     "When everyone zigs, the opportunity is in the zag."),
    ("Una marca es una promesa cumplida mil veces.",
     "A brand is a promise kept a thousand times."),
    ("La innovación es simplemente negarse a aceptar las cosas como son.",
     "Innovation is simply refusing to accept things as they are."),
    ("La parte más difícil de construir algo grande es empezar algo pequeño.",
     "The hardest part of building something great is starting something small."),
    ("La confianza es la moneda que se capitaliza más rápido que el dinero.",
     "Trust is the currency that compounds faster than capital."),
    ("No construyas una empresa que quieras vender. Construye una que el mundo necesite.",
     "Do not build a company you want to sell. Build one the world needs."),
    ("Estrategia sin ejecución es una hermosa alucinación.",
     "Strategy without execution is a beautiful hallucination."),
    ("La única ventaja competitiva sostenible es la capacidad de aprender más rápido.",
     "The only sustainable competitive advantage is the ability to learn faster."),
    ("Las oportunidades no se anuncian. Tienes que ir a buscarlas.",
     "Opportunities do not announce themselves. You have to go find them."),
    ("Toda crisis contiene las semillas de la próxima gran empresa.",
     "Every crisis contains the seeds of the next great enterprise."),
    ("Si eres la persona más inteligente en cada reunión, estás construyendo el equipo equivocado.",
     "If you are the smartest person in every meeting, you are building the wrong team."),
    ("La ambición global requiere humildad local.",
     "Global ambition requires local humility."),
    ("Una decisión tomada tarde es peor que una decisión tomada de forma imperfecta.",
     "A decision made too late is worse than a decision made imperfectly."),
    ("La facturación es vanidad, el beneficio es cordura, el flujo de caja es realidad.",
     "Revenue is vanity, profit is sanity, cash flow is reality."),
    ("Las mejores alianzas se construyen sobre valores compartidos, no intereses compartidos.",
     "The best partnerships are built on shared values, not shared interests."),
    ("Los emprendedores no predicen el futuro. Lo crean.",
     "Entrepreneurs do not predict the future. They create it."),
    ("No puedes escalar lo que no puedes explicar con sencillez.",
     "You cannot scale what you cannot explain simply."),
    ("El carácter se revela no en cómo ganas, sino en cómo respondes a los reveses.",
     "Character is revealed not in how you win, but in how you respond to setbacks."),
    ("Una empresa sin valores es un barco sin brújula.",
     "An enterprise without values is a ship without a compass."),
    ("No esperes el momento perfecto. Haz que el momento sea lo suficientemente perfecto.",
     "Do not wait for the perfect moment. Make the moment perfect enough."),
    ("Crecer por crecer es la ideología de una célula cancerosa. Crece con propósito.",
     "Growth for the sake of growth is the ideology of a cancer cell. Grow with purpose."),
    ("La frase más peligrosa en los negocios es: siempre lo hemos hecho así.",
     "The most dangerous phrase in business is: we have always done it this way."),
    ("La gente no compra productos. Compra versiones mejores de sus propias vidas.",
     "People do not buy products. They buy better versions of their own lives."),
    ("La disciplina en las pequeñas cosas construye credibilidad para las grandes.",
     "Discipline in small things builds credibility for big things."),
    ("Si quieres ir rápido, ve solo. Si quieres llegar lejos, construye una empresa.",
     "If you want to go fast, go alone. If you want to go far, build a company."),
    ("El riesgo es el impuesto que pagas por rendimientos extraordinarios.",
     "Risk is the tax you pay for extraordinary returns."),
    ("Al mercado no le importan tus intenciones. Le importan tus resultados.",
     "The market does not care about your intentions. It cares about your results."),
    ("Tu primer deber como fundador es sobrevivir. Todo lo demás viene después.",
     "Your first duty as a founder is to survive. Everything else follows."),
    ("Una marca fuerte es una historia de la que la gente quiere formar parte.",
     "A strong brand is a story people want to be part of."),
    ("La ética no es una restricción. Es la base del éxito duradero.",
     "Ethics are not constraints. They are the foundation of durable success."),
    ("No necesitas ser el primero. Necesitas ser quien lo haga bien.",
     "You do not need to be first. You need to be the one who gets it right."),
    ("Los problemas complejos requieren principios simples aplicados sin descanso.",
     "Complex problems require simple principles applied relentlessly."),
    ("La riqueza creada con responsabilidad perdura más que la riqueza extraída con avaricia.",
     "Wealth created responsibly outlasts wealth extracted recklessly."),
    ("El emprendedor ve un vacío y construye un puente. El pesimista ve un vacío y construye un muro.",
     "The entrepreneur sees a gap and builds a bridge. The pessimist sees a gap and builds a wall."),
    ("Las grandes empresas sobreviven a sus fundadores porque la misión es más grande que cualquier persona.",
     "Great companies outlive their founders because the mission is bigger than any one person."),
    ("Negociar no es ganar. Es crear acuerdos que valga la pena mantener.",
     "Negotiation is not about winning. It is about creating agreements worth keeping."),
    ("La innovación sin empatía produce tecnología que nadie pidió.",
     "Innovation without empathy produces technology nobody asked for."),
    ("Una empresa que no invierte en su gente está pidiendo prestado de su propio futuro.",
     "A company that does not invest in its people is borrowing from its own future."),
    ("El coste de la inacción siempre supera el coste de la acción imperfecta.",
     "The cost of inaction always exceeds the cost of imperfect action."),
    ("Construye para tus clientes, no para tu ego.",
     "Build for your customers, not for your ego."),
    ("La resiliencia no es nunca caer. Es lo rápido que te levantas.",
     "Resilience is not about never falling. It is about how quickly you rise."),
    ("Toda gran fortuna comenzó con un solo acto irracional de fe.",
     "Every great fortune began with a single, unreasonable act of belief."),
    ("La simplicidad es la máxima sofisticación en los negocios.",
     "Simplicity is the ultimate sophistication in business."),
    ("Los mejores emprendedores son estudiantes incansables del comportamiento humano.",
     "The best entrepreneurs are relentless students of human behavior."),
    ("Tu red de contactos no es tu patrimonio. Tu reputación sí lo es.",
     "Your network is not your net worth. Your reputation is."),
    ("Una visión sin calendario es solo un deseo.",
     "A vision without a timeline is just a wish."),
    ("No confundas actividad con progreso. Solo los resultados importan.",
     "Do not confuse activity with progress. Only results matter."),
    ("El mundo necesita más constructores y menos espectadores.",
     "The world needs more builders and fewer spectators."),
    ("El verdadero liderazgo se mide por el éxito de aquellos a quienes empoderas.",
     "True leadership is measured by the success of those you empower."),
    ("Crea valor que trascienda los informes trimestrales.",
     "Create value that transcends quarterly reports."),
    ("Las empresas más fuertes se construyen en los tiempos más difíciles.",
     "The strongest companies are built during the hardest times."),
    ("Lo que toleras en tu organización, lo apruebas.",
     "What you tolerate in your organization, you endorse."),
    ("La ambición sin integridad es un fuego sin hogar.",
     "Ambition without integrity is a fire without a hearth."),
]

# ──────────────────────────────────────────────────────────────────────────
# BLOG highlights — real articles on manzanosenterprises.com/news.
# image = filename inside the website's public/images/hero (see make_me.SOURCE_HERO).
# Texts are verbatim from the live /es site (kept consistent on purpose).
# Add new ones on top; the engine rotates through all of them.
# ──────────────────────────────────────────────────────────────────────────
BLOG = [
    {"slug": "boring-work-that-wins-management-systems-kpis-compound-over-decades",
     "image": "mhsa.jpg",
     "title_es": "El trabajo aburrido que gana",
     "title_en": "The Boring Work That Wins",
     "hook_es": "A la mayoría de las empresas no las mata un competidor: las mata la erosión lenta del trabajo poco glamuroso. Así un sistema de gestión construye una empresa que compone durante décadas.",
     "hook_en": "Most companies are not killed by a competitor — they are killed by the slow erosion of the unglamorous work. How a management system compounds across eight industries."},
    {"slug": "the-deals-you-dont-do-walk-away-discipline-smart-acquisitions",
     "image": "palacio-exterior.jpg",
     "title_es": "Los acuerdos que no haces",
     "title_en": "The Deals You Don't Do",
     "hook_es": "Las adquisiciones que construyeron nuestro grupo importan menos que las que rechazamos. La disciplina de retirarse que protege a una empresa diversificada.",
     "hook_en": "The acquisitions that built our group matter less than the ones we refused. The walk-away discipline that protects a diversified company."},
    {"slug": "ai-heritage-businesses-adopt-technology-without-losing-soul",
     "image": "1890-finca-manzanos.jpg",
     "title_es": "IA en una empresa de 130 años",
     "title_en": "AI in a 130-Year-Old Company",
     "hook_es": "Las empresas con historia fracasan con la tecnología de dos formas: no adoptan nada, o lo adoptan todo. Conservar el oficio, automatizar la fricción.",
     "hook_en": "Heritage businesses fail at technology two ways: adopt nothing, or adopt everything. Keep the craft, automate the friction."},
    {"slug": "choosing-the-right-distributor-enter-foreign-market-without-losing-brand",
     "image": "miami.jpg",
     "title_es": "Elegir al distribuidor adecuado",
     "title_en": "Choosing the Right Distributor",
     "hook_es": "Cómo entrar en un mercado extranjero sin entregar tu marca. Elegir mal a un distribuidor puede enterrar una marca en un almacén durante años.",
     "hook_en": "How to enter a foreign market without handing over your brand. The wrong distributor can bury a brand in a warehouse for years."},
    {"slug": "heritage-is-a-moat-you-cannot-buy-brand-competitive-advantage",
     "image": "legacy-v2.jpg",
     "title_es": "El patrimonio es un foso que no se puede comprar",
     "title_en": "Heritage Is a Moat You Cannot Buy",
     "hook_es": "Un competidor puede copiar tu producto en un trimestre. Lo que nadie puede copiar es el tiempo que costó ganarse la confianza.",
     "hook_en": "A competitor can copy your product in a quarter. What no one can copy is the time it took to earn trust."},
    {"slug": "when-to-let-a-leader-go-decision-founders-delay-too-long",
     "image": "palacio-de-manzanos.jpg",
     "title_es": "Cuándo dejar ir a un líder",
     "title_en": "When to Let a Leader Go",
     "hook_es": "La decisión que los fundadores retrasan demasiado — y lo que cuesta. La decisión de liderazgo más difícil no es a quién contratar.",
     "hook_en": "The decision founders delay too long — and what it costs. The hardest leadership call is not who to hire."},
    {"slug": "centralize-or-decentralize-operating-model-multi-business-owners",
     "image": "hero-interior.jpg",
     "title_es": "¿Centralizar o descentralizar?",
     "title_en": "Centralize or Decentralize?",
     "hook_es": "Qué funciones pertenecen al centro y cuáles al borde. El marco para dirigir ocho negocios muy distintos sin asfixiar a ninguno.",
     "hook_en": "Which functions belong at the center, which at the edge. The framework for running eight businesses without strangling any."},
    {"slug": "the-long-middle-why-most-businesses-quit-in-the-years-nobody-writes-about",
     "image": "legacy.jpg",
     "title_es": "El largo medio",
     "title_en": "The Long Middle",
     "hook_es": "La mayoría de los negocios no mueren al principio: abandonan en los años de los que nadie escribe. La persistencia es una estrategia.",
     "hook_en": "Most businesses don't die at the start — they quit in the years nobody writes about. Persistence is a strategy."},
    {"slug": "where-every-euro-goes-capital-allocation-discipline-that-compounds",
     "image": "miami.jpg",
     "title_es": "Adónde va cada euro",
     "title_en": "Where Every Euro Goes",
     "hook_es": "La disciplina de asignación de capital que separa a los grupos que componen de los que se estancan. Reinvertir, adquirir, amortizar o repartir.",
     "hook_en": "The capital allocation discipline that separates groups that compound from groups that stall."},
    {"slug": "patient-capital-why-thinking-in-decades-beats-thinking-in-quarters",
     "image": "1890-finca-manzanos.jpg",
     "title_es": "Capital paciente",
     "title_en": "Patient Capital",
     "hook_es": "Por qué pensar en décadas vence a pensar en trimestres. Los mejores rendimientos pertenecen a quien está dispuesto a esperar.",
     "hook_en": "Why thinking in decades beats thinking in quarters. The best returns belong to those willing to wait."},
    {"slug": "succession-is-a-system-family-businesses-beat-third-generation-curse",
     "image": "legacy-v3.jpg",
     "title_es": "La sucesión es un sistema, no un acontecimiento",
     "title_en": "Succession Is a System, Not an Event",
     "hook_es": "Cómo las empresas familiares vencen la maldición de la tercera generación. Un sistema construido durante décadas, no un relevo dramático.",
     "hook_en": "How family businesses beat the third-generation curse — a system built over decades, not a dramatic handover."},
    {"slug": "culture-that-travels-keeping-company-values-across-countries-and-industries",
     "image": "1890-finca-manzanos.jpg",
     "title_es": "Una cultura que viaja",
     "title_en": "Culture That Travels",
     "hook_es": "Un grupo en ocho industrias no se mantiene unido con un manual de procesos. Se mantiene unido con la cultura.",
     "hook_en": "A group across eight industries isn't held together by a process manual. It's held together by culture."},
    {"slug": "pricing-power-build-business-raise-prices-without-losing-customers",
     "image": "palacio-detalle.jpg",
     "title_es": "Poder de precio",
     "title_en": "Pricing Power",
     "hook_es": "Cómo construir un negocio que puede subir precios sin perder clientes. La característica financiera más valiosa que puede tener un negocio.",
     "hook_en": "How to build a business that can raise prices without losing customers — the most valuable financial trait a business can own."},
    {"slug": "divestiture-decision-when-to-sell-spin-off-or-close-a-business",
     "image": "legacy-v3.jpg",
     "title_es": "La decisión de desinvertir",
     "title_en": "The Divestiture Decision",
     "hook_es": "Saber qué dejar es lo que separa a los operadores que componen capital de los que lo desangran. Cuándo vender, escindir o cerrar.",
     "hook_en": "Knowing what to exit separates operators who compound capital from those who bleed it. When to sell, spin off, or close."},
    {"slug": "geographic-expansion-sequencing-order-of-markets-matters-more-than-markets",
     "image": "hero-v2.jpg",
     "title_es": "Secuenciación de la expansión geográfica",
     "title_en": "Geographic Expansion Sequencing",
     "hook_es": "Por qué el orden en que entras a los mercados importa más que los mercados mismos. Qué país va primero, cuál segundo y cuáles esperan.",
     "hook_en": "Why the order of markets you enter matters more than the markets themselves."},
    {"slug": "acquisition-engine-repeatable-ma-capability-founder-led-companies",
     "image": "mhsa-v2.jpg",
     "title_es": "El motor de adquisiciones",
     "title_en": "The Acquisition Engine",
     "hook_es": "Las empresas que componen riqueza mediante adquisiciones no apuestan: construyen motores. Una capacidad repetible de M&A.",
     "hook_en": "Companies that compound wealth through acquisitions don't bet — they build engines. A repeatable M&A capability."},
]

# Base URL of the public site (used to build the article link in captions).
SITE = "https://www.manzanosenterprises.com"

# ──────────────────────────────────────────────────────────────────────────
# LIVE SOURCE OF TRUTH: quotes.json / blog.json (grow over time)
# The literals above are the seed/fallback. The refresh jobs APPEND new entries
# to these JSON files — never edit the Python. If a JSON file is missing or
# unreadable, we fall back to the embedded seed so the system never breaks.
# ──────────────────────────────────────────────────────────────────────────
import json as _json, os as _os
_DIR = _os.path.dirname(_os.path.abspath(__file__))
def _load(name, fallback):
    p = _os.path.join(_DIR, name)
    if _os.path.exists(p):
        try:
            data = _json.load(open(p, encoding="utf-8"))
            if data:
                return data
        except Exception:
            pass
    return fallback
QUOTES = [tuple(q) for q in _load("quotes.json", QUOTES)]
BLOG = _load("blog.json", BLOG)


def quote_count():
    return len(QUOTES)


def blog_count():
    return len(BLOG)


if __name__ == "__main__":
    print(f"{quote_count()} quotes · {blog_count()} blog highlights")
