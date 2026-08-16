# **Análisis Forense de la Maquetación Digital del Verso: Patrones Estructurales, Semántica del DOM y Diagnóstico de Corrupción en el Ecosistema EPUB y Kindle**

## **La Arquitectura Líquida y la Inviolabilidad de la Línea de Verso**

La transposición del texto lírico, la poesía visual y el teatro clásico en verso desde la página estática bidimensional al flujo adaptable de los dispositivos de lectura digital representa uno de los desafíos más complejos en la ingeniería del libro electrónico1. A diferencia del texto en prosa, donde la descomposición de la línea es arbitraria y depende exclusivamente de las dimensiones físicas de la pantalla y de las preferencias de visualización del usuario, en la poesía la línea es una unidad estructural, métrica y semántica inviolable1. La fragmentación descontrolada de un verso debido al escalado tipográfico altera la respiración, el ritmo y la intención del autor, reduciendo el poema a un híbrido amorfo y rompiendo el pacto de lectura original1.  
Para resolver la tensión entre adaptabilidad y rigidez visual, el ecosistema de la edición digital se ha dividido históricamente en dos aproximaciones técnicas: el uso de maquetación fija (Fixed Layout o FXL), que suprime la accesibilidad y el escalado de fuentes a cambio de fidelidad absoluta, y el diseño adaptable (Reflowable EPUB), que busca emular la estructura de la página impresa mediante hojas de estilo en cascada (CSS) avanzadas y metadatos estructurales del DOM1.  
El presente informe detalla el análisis forense de estas estructuras a lo largo de todo el espectro editorial europeo y americano, evaluando las soluciones semánticas y visuales implementadas tanto por comunidades de preservación de código abierto como por grandes conglomerados, sellos independientes y suites automáticas de exportación3.

## **Tipología 1: Comunidades Independientes y Plataformas de Preservación**

Las comunidades de digitalización voluntaria y las iniciativas de código abierto para la preservación de bienes comunes digitales han desarrollado estructuras de marcado con una marcada divergencia técnica. Mientras que algunas plataformas cargan con el legado del texto plano convertido de forma automática, otras han sistematizado la semántica XML más rigurosa disponible en el estándar EPUB 33.

### **Standard Ebooks**

La comunidad de Standard Ebooks representa el nivel más sofisticado de marcado semántico en el dominio público mundial10. Su metodología rechaza las soluciones de formateo visual e implementa de manera estricta el vocabulario estructural Z39.98 de la Alianza DAISY y los namespaces semánticos de EPUB 33. En sus ediciones, cada obra poética se organiza utilizando elementos de sección conformes a HTML53.  
Un poema individual dentro de una colección se encapsula dentro de una etiqueta \<article\>3. Las estrofas se representan mediante elementos de párrafo \<p\> y cada verso individual se introduce dentro de un elemento \<span\> configurado con sangría francesa (hanging indent) proporcional mediante CSS3. Esto garantiza que si el verso se desborda debido a una pantalla estrecha o un tamaño de fuente elevado, la parte desbordada se muestre con una sangría clara, preservando la identidad de la línea inicial1.  
Adicionalmente, implementan un control físico mediante saltos \<br/\> colocados inmediatamente después de cada elemento \<span\>, excepto en el último verso de la estrofa3. Para los motores de renderizado modernos que procesan correctamente CSS de nivel 3, el salto de línea físico se oculta asignando la regla display: none al selector correspondiente, impidiendo duplicaciones visuales de espacio3. Las elisiones métricas se controlan mediante el carácter de puntos suspensivos verticales (⋮ o U+22EE) dentro de una clase específica que mantiene el espaciado rítmico7.

#### **Fragmento XHTML (Standard Ebooks):**

XML  
\<article xmlns:epub\="<http://www.idpf.org/2007/ops>"
         epub:prefix\="z3998: <http://www.daisy.org/z3998/2012/vocab/structure/>"
         id\="poem-1"
         epub:type\="z3998:poem"\>  
  \<header\>  
    \<h2 epub:type\="title"\>A un olmo seco\</h2\>  
  \</header\>  
  \<p\>  
    \<span\>Al olmo viejo, hendido por el rayo\</span\>\<br/\>  
    \<span\>y en su mitad podrido,\</span\>\<br/\>  
    \<span class\="i1"\>con las lluvias de abril y el sol de mayo,\</span\>\<br/\>  
    \<span\>algunas hojas verdes le han salido.\</span\>  
  \</p\>  
  \<p\>  
    \<span\>El olmo centenario en la colina\</span\>\<br/\>  
    \<span class\="elision"\>⋮\</span\>\<br/\>  
    \<span\>Antes que te derribe, olmo del Duero.\</span\>  
  \</p\>  
\</article\>

#### **Fragmento CSS Asociado:**

CSS  
@namespace epub "<http://www.idpf.org/2007/ops>";

/\* Bloque contenedor y estrofas \*/  
\[epub|type\~="z3998:poem"\] p {  
    text-align: initial;  
    text-indent: 0;  
}

\[epub|type\~="z3998:poem"\] p \+ p {  
    margin-top: 1.0em;  
}

/\* Control del desborde de línea en versos mediante sangría francesa \*/  
\[epub|type\~="z3998:poem"\] p \> span {  
    display: block;  
    padding-left: 1.5em;  
    text-indent: \-1.5em;  
}

/\* Ocultación de saltos de línea físicos en motores conformes \*/  
\[epub|type\~="z3998:poem"\] p \> span \+ br {  
    display: none;  
}

/\* Estilos de indentación métrica variable \*/  
p span.i1 {  
    padding-left: 2.5em;  
    text-indent: \-1.5em;  
}

p span.i2 {  
    padding-left: 3.5em;  
    text-indent: \-1.5em;  
}

/\* Elisión semántica vertical \*/  
span.elision {  
    display: block;  
    margin-top: 0.5em;  
    margin-bottom: 0.5em;  
    margin-left: 3.0em;  
}

### **Proyecto Gutenberg, Epublibre, Liber Liber y Progetto Manuzio**

En el otro extremo de las plataformas independientes se sitúan los repositorios históricos cuyo origen es la conversión automatizada de archivos de texto plano (ASCII o ISO-8859-1)8. Proyecto Gutenberg y Epublibre a menudo presentan estructuras híbridas donde el verso se formatea emulando el espaciado físico original mediante etiquetas de texto preformateado (\<pre\>) o forzando márgenes de párrafo y el uso de entidades de espacio duro ( ) para simular sangrías3. Las plataformas italianas (Progetto Manuzio y Liber Liber) y los archivos nacionales europeos a menudo heredan plantillas XHTML básicas del formato EPUB 2, donde la semántica se diluye en clases genéricas aplicadas a nivel de bloque9.

#### **Fragmento XHTML (Legacy Gutenberg / Epublibre):**

HTML  
\<div class\="poesia\_legacy"\>  
  \<p class\="verso\_legacy"\>Nel mezzo del cammin di nostra vita\</p\>  
  \<p class\="verso\_legacy\_indetato"\>    mi ritrovai per una selva oscura,\</p\>  
  \<p class\="verso\_legacy"\>ché la diritta via era smarrita.\</p\>  
\</div\>

#### **Lista de Cadenas para Diccionario Python (Comunidades):**

Python  
COMUNIDADES\_STRINGS \= {  
    "containers": \[  
        "poesia\_legacy", "poem-container", "poetry-block", "gutenberg-poem",
        "epublibre-poema", "manuzio-versi", "liber-liber-poema", "bloque-poetico"  
    \],  
    "stanzas": \[  
        "stanza", "estrofa", "v-group", "verse-group", "gutenberg-stanza", "estrofa-legacy"  
    \],  
    "lines": \[  
        "v-line", "verso\_legacy", "gutenberg-line", "l-verso", "linea-poesia"  
    \],  
    "indents": \[  
        "verso\_legacy\_indetato", "i1", "i2", "i3", "indent-1", "indent-2", "sangria-1"  
    \]  
}

## **Tipología 2: Grandes Conglomerados Editoriales y Prensas Académicas**

Las grandes corporaciones editoriales occidentales operan bajo flujos de trabajo masivos de conversión (XML-first o InDesign a EPUB)5. Los requisitos de velocidad y uniformidad corporativa conducen a hojas de estilo altamente estandarizadas, pero frecuentemente sobrecargadas con clases de diseño propietario que revelan la herencia del diseño de impresión5.

### **Penguin Random House, Grupo Planeta, Simon & Schuster y HarperCollins**

Los flujos de exportación de estos gigantes editoriales se caracterizan por el uso de prefijos corporativos en los nombres de las clases, destinados a evitar conflictos tipográficos al fusionar componentes dentro de sus sistemas de gestión de activos digitales. Utilizan identificadores semánticos en menor medida que Standard Ebooks, priorizando la compatibilidad absoluta entre dispositivos de lectura heredados como los primeros Kindle o lectores de tinta electrónica de gama baja17.

#### **Fragmento XHTML (Penguin Random House):**

HTML  
\<div class\="prh-poetry-wrapper" role\="doc-poem"\>  
  \<div class\="prh-stanza-block"\>  
    \<p class\="prh-verse-line"\>Paseábase el rey moro\</p\>  
    \<p class\="prh-verse-line prh-verse-indent-1"\>por la ciudad de Granada,\</p\>  
    \<p class\="prh-verse-line"\>desde la puerta de Elvira\</p\>  
    \<p class\="prh-verse-line prh-verse-indent-1"\>hasta la de Vivarrambla.\</p\>  
  \</div\>  
\</div\>

#### **Fragmento CSS Asociado:**

CSS  
.prh-poetry-wrapper {  
    margin-top: 2.0em;  
    margin-bottom: 2.0em;  
    padding-left: 10%;  
    padding-right: 10%;  
}

.prh-stanza-block {  
    margin-bottom: 1.5em;  
    page-break-inside: avoid; /\* Intenta evitar rotura de estrofa entre páginas \*/  
}

.prh-verse-line {  
    display: block;  
    text-align: left;  
    text-indent: \-1.5em;  
    padding-left: 1.5em;  
    margin: 0 0 0.2em 0;  
}

.prh-verse-indent-1 {  
    padding-left: 3.0em;  
}

### **Oxford University Press y Cambridge University Press**

Las editoriales académicas anglosajonas se enfrentan al reto adicional de maquetar ediciones críticas de poesía, teatro isabelino y textos clásicos anotados4. Sus estructuras de datos en el DOM son muy avanzadas e integran números de línea automáticos o manuales colocados mediante elementos flotantes en el margen izquierdo o derecho, además de soporte para diálogo poético (actantes)19.

#### **Fragmento XHTML (Cambridge University Press \- Teatro en Verso):**

HTML  
\<section id\="act-3-scene-1" epub:type\="chapter"\>  
  \<h3 class\="scene-title"\>SCENE I. Elsinore. A room in the Castle.\</h3\>  
  \<div class\="drama-play-container" epub:type\="z3998:play"\>  
    \<div class\="speech-block"\>  
      \<span class\="actant-name"\>HAMLET\</span\>  
      \<div class\="speech-lines" epub:type\="z3998:verse"\>  
        \<p class\="v-line"\>\<span class\="line-num"\>56\</span\>To be, or not to be, that is the question:\</p\>  
        \<p class\="v-line"\>\<span class\="line-num"\>57\</span\>Whether ’tis nobler in the mind to suffer\</p\>  
        \<p class\="v-line"\>\<span class\="line-num"\>58\</span\>The slings and arrows of outrageous fortune,\</p\>  
      \</div\>  
    \</div\>  
  \</div\>  
\</section\>

#### **Fragmento CSS Asociado:**

CSS  
.drama-play-container {  
    margin-left: 5%;  
    margin-right: 5%;  
}

.speech-block {  
    margin-top: 1.2em;  
    margin-bottom: 1.2em;  
}

.actant-name {  
    display: block;  
    font-weight: bold;  
    font-size: 0.9em;  
    text-transform: uppercase;  
    margin-bottom: 0.4em;  
    letter-spacing: 0.05em;  
}

.speech-lines p.v-line {  
    position: relative;  
    display: block;  
    text-indent: \-2.0em;  
    padding-left: 2.0em;  
    margin: 0;  
}

.line-num {  
    position: absolute;  
    left: \-1.5em;  
    font-size: 0.7em;  
    color: \#666666;  
    font-family: monospace, sans-serif;  
    text-indent: 0;  
}

#### **Lista de Cadenas para Diccionario Python (Conglomerados y Académicas):**

Python  
CONGLOMERADOS\_STRINGS \= {  
    "containers": \[  
        "prh-poetry-wrapper", "planeta-poetry", "simon-schuster-poem", "harper-verse",  
        "cup-poetry-container", "oup-poetry-critical", "drama-play-container", "play-block"  
    \],  
    "stanzas": \[  
        "prh-stanza-block", "planeta-estrofa", "stanza-container", "speech-lines"  
    \],  
    "lines": \[  
        "prh-verse-line", "v-line", "planeta-verso", "oup-verse-critical"  
    \],  
    "indents": \[  
        "prh-verse-indent-1", "prh-verse-indent-2", "v-line-indented", "line-num"  
    \]  
}

## **Tipología 3: Editoriales Independientes, Medianas y Microeditoriales**

Las editoriales independientes y de especialidad lírica (Visor Libros, Hiperión, Editorial Pre-Textos, Lumen en España e Hispanoamérica; New Directions, Faber & Faber en el ámbito anglosajón) dan prioridad absoluta a la fidelidad visual y estética sobre la uniformidad de los flujos de exportación industrial6. Ello los empuja a diseñar soluciones de maquetación altamente customizadas y, a menudo, a librar batallas técnicas contra las limitaciones de visualización de los entornos propietarios6.

### **New Directions y Faber & Faber**

La gestión de libros digitales de poesía en sellos independientes ha estado históricamente vinculada a la experimentación técnica6. Un caso paradigmático es el de New Directions, que ha documentado la lucha contra los motores de renderizado de Amazon Kindle Previewer (KP3)18.  
Los entornos de Amazon tienden a forzar de manera destructiva capitales o capitulares flotantes (drop-caps) sobre elementos iniciales, aplicando clases globales que desalinean el primer verso del poema si se confunde con prosa convencional18. Para resolver esto, los diseñadores de New Directions aplican técnicas que anulan la flotación en los versos y diseñan hojas de estilo que obligan a anular los saltos de página dentro de una misma estrofa (page-break-inside: avoid)18.

#### **Fragmento XHTML (New Directions \- Verso Libre):**

HTML  
\<div class\="nd-poetry-container"\>  
  \<div class\="nd-stanza"\>  
    \<span class\="nd-verse-line"\>Water is a dry substance\</span\>\<br/\>  
    \<span class\="nd-verse-line nd-indent-medium"\>that is easily wet\</span\>\<br/\>  
    \<span class\="nd-verse-line"\>by things that are not dry.\</span\>  
  \</div\>  
\</div\>

#### **Fragmento CSS Asociado:**

CSS  
.nd-poetry-container {  
    margin-left: 15%;  
    margin-right: 10%;  
    font-variant\-numeric: oldstyle-nums;  
}

.nd-stanza {  
    margin-bottom: 2.0em;  
    page-break-inside: avoid;  
}

.nd-verse-line {  
    display: inline-block; /\* Evita que el renderizador de Kindle rompa el flujo \*/  
    width: 100%;  
    text-indent: \-2.0em;  
    padding-left: 2.0em;  
    word-break: keep-all;  
    hyphens: none \!important; /\* Esencial para preservar la métrica sin silabaciones arbitrarias \*/  
}

.nd-indent-medium {  
    padding-left: 4.0em;  
}

### **Ámbito Hispánico: Visor Libros, Hiperión, Pre-Textos y Sellos de América Latina**

En España y América Latina (México, Argentina, Colombia, Chile), las editoriales independientes de poesía recurren de forma frecuente al diseño de libros bilingües (edición con traducción enfrentada). Esto plantea una dificultad extrema en pantallas pequeñas reflowable, forzando a los maquetadores a crear estructuras de tabla invisibles o bloques dobles que se alternan según la orientación del dispositivo22.

#### **Fragmento XHTML (Pre-Textos \- Edición Bilingüe):**

HTML  
\<div class\="bilingual-poetry-block"\>  
  \<div class\="original-poem-column"\>  
    \<p class\="pt-original-verse"\>Sempre il vento del nord trae la tempesta,\</p\>  
  \</div\>  
  \<div class\="translated-poem-column"\>  
    \<p class\="pt-translated-verse"\>Siempre el viento del norte trae la tormenta,\</p\>  
  \</div\>  
\</div\>

#### **Fragmento CSS Asociado:**

CSS  
.bilingual-poetry-block {  
    display: flex;  
    flex-direction: row;  
    justify-content: space-between;  
    width: 100%;  
}

.original-poem-column,
.translated-poem-column {  
    width: 48%;  
    font-size: 0.85em;  
}

@media (max-width: 600px) {  
    /\* Hack de transformación líquida: apila las versiones si el ancho de pantalla es crítico \*/  
    .bilingual-poetry-block {  
        display: block;  
    }  
    .original-poem-column,
    .translated-poem-column {  
        width: 100%;  
        display: block;  
        margin-bottom: 1.5em;  
    }  
}

#### **Lista de Cadenas para Diccionario Python (Editoriales Independientes):**

Python  
INDEPENDIENTES\_STRINGS \= {  
    "containers": \[  
        "nd-poetry-container", "faber-poetry-block", "visor-bilingue", "hiperion-poema",  
        "pre-textos-poema", "lumen-lirico", "bilingual-poetry-block", "original-poem-column"  
    \],  
    "stanzas": \[  
        "nd-stanza", "faber-stanza", "pt-stanza", "visor-estrofa", "hiperion-estrofa"  
    \],  
    "lines": \[  
        "nd-verse-line", "pt-original-verse", "pt-translated-verse", "visor-verso", "hiperion-v"  
    \],  
    "indents": \[  
        "nd-indent-medium", "nd-indent-deep", "pt-sangria", "visor-sangrado"  
    \]  
}

## **Tipología 4: Herramientas de Software de Maquetación Automática**

La gran mayoría de los libros electrónicos presentes en tiendas comerciales no se programa de manera manual, sino que se exporta desde plataformas de edición23. Estas herramientas inyectan esquemas de clases e IDs redundantes y con escasa semántica, característicos de sus motores de traducción XML internos5.

### **Adobe InDesign**

InDesign genera identificadores CSS derivados de los estilos de párrafo creados por el maquetador físico del volumen5. Si no se mapean las clases manualmente a etiquetas poéticas nativas del estándar digital, la suite produce una sucesión de clases enumeradas (\_idGenParagraphStyle-X) y envoltorios de objeto genéricos (\_idGenObjectAttribute-Y) que carecen por completo de intencionalidad semántica5.

#### **Fragmento XHTML (InDesign):**

HTML  
\<div id\="\_idContainer001" class\="\_idGenObjectAttribute-1"\>  
  \<p class\="Poesia\_Verso\_Normal \_idGenParagraphStyle-1"\>En la mañana azul, bajo el alero,\</p\>  
  \<p class\="Poesia\_Verso\_Normal \_idGenParagraphStyle-1"\>donde cantaba alegre el benteveo.\</p\>  
  \<p class\="Poesia\_Verso\_Sangrado \_idGenParagraphStyle-2"\>Un susurro lejano de arboleda...\</p\>  
\</div\>

#### **Fragmento CSS Asociado:**

CSS  
p.\_idGenParagraphStyle-1 {  
    font-family: "Minion Pro", serif;  
    font-size: 11px;  
    line-height: 14px;  
    text-align: left;  
    text-indent: 0px;  
    margin-bottom: 0px;  
    margin-top: 0px;  
}

p.\_idGenParagraphStyle-2 {  
    font-family: "Minion Pro", serif;  
    font-size: 11px;  
    line-height: 14px;  
    text-align: left;  
    text-indent: 0px;  
    margin-bottom: 0px;  
    margin-top: 0px;  
    margin-left: 24px; /\* Sangría fija expresada en píxeles \*/  
}

### **Calibre**

Calibre inyecta clases predeterminadas numeradas correlativamente (calibre1, calibre2) y contenedores globales específicos como calibre\_poetry durante la conversión automática de archivos rtf o docx27. Sus algoritmos de re-escalado recalculan los tamaños relativos basándose en el análisis probabilístico de la fuente más común del manuscrito de entrada28.

#### **Fragmento XHTML (Calibre):**

HTML  
\<div class\="calibre\_poetry"\>  
  \<p class\="calibre1"\>Es el viento que pasa,\</p\>  
  \<p class\="calibre1"\>es la noche que llega...\</p\>  
  \<p class\="calibre2"\>y es la voz que nos llama.\</p\>  
\</div\>

### **Vellum**

El software de maquetación Vellum para macOS genera estructuras HTML muy limpias y visualmente estables, pero con una nula semántica de metadatos estructurales (sin uso de vocabularios Z39.98)29. La herramienta ofrece opciones específicas de visualización lírica para sus plantillas y gestiona de manera interna la supresión de párrafos vacíos que carecen de caracteres invisibles o de saltos controlados15.

#### **Fragmento XHTML (Vellum):**

HTML  
\<div class\="vellum-verse-container"\>  
  \<div class\="vellum-verse-alignment"\>  
    \<p class\="vellum-verse-first-line"\>Caminante, son tus huellas\</p\>  
    \<p class\="vellum-verse-line"\>el camino y nada más;\</p\>  
    \<p class\="vellum-verse-line"\>caminante, no hay camino,\</p\>  
    \<p class\="vellum-verse-last-line"\>se hace camino al andar.\</p\>  
  \</div\>  
\</div\>

#### **Fragmento CSS Asociado:**

CSS  
.vellum-verse-container {  
    margin-top: 2.0em;  
    margin-bottom: 2.0em;  
}

.vellum-verse-alignment {  
    display: inline-block;  
    text-align: left;  
}

.vellum-verse-line,
.vellum-verse-first-line,
.vellum-verse-last-line {  
    text-indent: \-1.5em;  
    padding-left: 1.5em;  
    margin: 0;  
}

.vellum-verse-last-line {  
    margin-bottom: 1.0em;  
}

### **Infogrid Pacific (IGP:FoundationXHTML)**

Las suites de producción industrial masiva de Infogrid Pacific aplican un sistema estructurado de clases basado en su propio estándar de nombres denominado FoundationXHTML4. Su marcado se distingue de manera inequívoca por el uso sistemático del sufijo \-rw (read-write) en todas las clases estructurales del DOM4.

#### **Fragmento XHTML (Infogrid Pacific):**

HTML  
\<div class\="poem-rw poem-normal-rw" epub:type\="z3998:poem"\>  
  \<div class\="poem-body-rw"\>  
    \<div class\="stanza-rw"\>  
      \<p class\="line-rw"\>Del salón en el ángulo oscuro,\</p\>  
      \<p class\="line-rw"\>de su dueña tal vez olvidada,\</p\>  
    \</div\>  
  \</div\>  
\</div\>

#### **Lista de Cadenas para Diccionario Python (Software):**

Python  
HERRAMIENTAS\_STRINGS \= {  
    "containers": \[  
        "calibre\_poetry", "vellum-verse-container", "vellum-verse-alignment",
        "poem-rw", "poem-normal-rw", "poem-body-rw", "\_idGenObjectAttribute",  
        "scrivener-verse"  
    \],  
    "stanzas": \[  
        "stanza-rw", "vellum-verse-block", "scrivener-stanza"  
    \],  
    "lines": \[  
        "line-rw", "vellum-verse-line", "vellum-verse-first-line",
        "vellum-verse-last-line", "calibre1", "calibre2", "Poesia\_Verso\_Normal",
        "Poesia\_Verso\_Sangrado", "\_idGenParagraphStyle"  
    \],  
    "indents": \[  
        "vellum-verse-indent", "indent-rw", "Poesia\_Verso\_Sangrado"  
    \]  
}

## **Análisis Forense de Malas Prácticas, Anomalías y "Hacks" Visuales**

El análisis masivo de libros electrónicos autoeditados o producidos mediante procesos de conversión de baja calidad ha revelado un catálogo recurrente de técnicas destructivas destinadas a forzar una apariencia visual determinada a expensas de la semántica y de la interoperabilidad del documento digital5.

### **1\. Salto de Línea Físico Consecutivo para Forzar Maquetación Vertical**

El uso masivo de saltos de línea \<br/\> consecutivos dentro de un único bloque de texto se utiliza con frecuencia para simular la distancia de separación entre estrofas o para forzar saltos de página artificiales5. Esta mala práctica rompe el comportamiento del motor de renderizado cuando el lector decide modificar las propiedades tipográficas globales del dispositivo de lectura5.

HTML  
\<\!-- CÓDIGO INCORRECTO: Acumulación de br para forzar espacio inter-estrofal \--\>  
\<p class\="verso"\>Y yo me iré. Y se quedarán los pájaros\</p\>  
\<br/\>  
\<br/\>  
\<p class\="verso"\>cantando;\</p\>

**Efecto forense**: Si el tamaño de letra se incrementa significativamente, estos saltos forzados se acumulan en el inicio de la siguiente pantalla física, produciendo un espacio en blanco insalvable o una página huérfana vacía dentro del lector digital31.

### **2\. Espacios en Blanco Unicode y Espacios Duros como Desplazadores Métricos**

Para imular los escalonamientos de versos de la poesía barroca o las formas lúdicas de las vanguardias hispanoamericanas, los maquetadores suelen recurrir al uso de entidades de espacio duro ( ) o carácteres invisibles de espacio Unicode de ancho específico, como En Space (\\u2002), Em Space (\\u2003) o Hair Space (\\u2009) inyectados al inicio de la cadena3.

HTML  
\<\!-- CÓDIGO INCORRECTO: Espacios manuales para forzar alineación métrica \--\>  
\<p class\="verso"\>        Pocas veces he visto tanto olvido...\</p\>  
\<p class\="verso"\>    En un cuerpo tan firme de ceniza.\</p\>

**Efecto forense**: Estos caracteres no se consideran márgenes físicos por los motores de renderizado CSS, por lo que bloquean las rutinas internas de justificación tipográfica y desalinean el bloque poético completo si la pantalla tiene dimensiones limitadas (por ejemplo, en la pantalla de un smartphone de pantalla estrecha)1.

### **3\. Modificadores CSS Inline Destructivos con \!important**

La incrustación de estilos directamente sobre los elementos del DOM inhabilita la cascada del CSS principal de la publicación y anula las preferencias de los motores de lectura de las aplicaciones (por ejemplo, el modo noche o los esquemas de accesibilidad para lectores con dislexia)32.

HTML  
\<\!-- CÓDIGO INCORRECTO: Inyección inline destructiva \--\>  
\<p class\="verso" style\="padding-left: 12% \!important; margin-right: 15% \!important; text-align: justify \!important;"\>La herida que no cesa de latir...\</p\>

## **Patrones de Corrupción Semántica en Ámbitos Hispanos (Mojibake)**

En las producciones editoriales de España, Portugal y América Latina (con gran énfasis en sellos pequeños o históricos que reutilizan archivos de texto de bases de datos heredadas), el fallo de conversión en la codificación de caracteres representa una de las anomalías semánticas más generalizadas8.  
Cuando las hojas de estilo o los archivos XHTML se procesan asumiendo codificaciones incompatibles con los flujos estándar (como el procesamiento de un archivo guardado con codificación Windows-1252 o ISO-8859-1 interpretado de forma errónea como un archivo UTF-8 por el empaquetador del EPUB), los nombres de las clases CSS sufren una mutación en sus caracteres especiales (tildes, eñes)8.  
![][image1]  
Esto genera una divergencia fatal entre los selectores declarados en el archivo CSS y los nombres de las clases asignadas en el documento XHTML, rompiendo toda la maquetación y aplicando estilos planos de prosa a los poemas de la publicación25.

| Nombre de Clase Original Esperado | Expresión Corrupta en XHTML (Mojibake) | Patrón de Byte Corrupto detectado | Efecto Crítico en la Visualización |
| :---- | :---- | :---- | :---- |
| class="poesía" | class="poes-a" o class="poesÃa" | 0xC3 0xAD (Secuencia UTF-8 de "í") | Anulación total de la hoja de estilo del contenedor. El poema se muestra como prosa de corrido25. |
| class="sangría" | class="sangr-a" o class="sangrÃa" | 0xC3 0xAD (Secuencia UTF-8 de "í") | Pérdida de la sangría francesa; los versos desbordados se rompen alineándose al margen izquierdo32. |
| class="estrofa" | class="estrof-" o class="estrof\_" | 0x2D (Guión por truncamiento de sistema) | Pérdida de la regla de espacio inter-estrofal, unificando todo el poema de manera vertical. |
| class="canción" | class="canci-n" o class="canciÃ³n" | 0xC3 0xB3 (Secuencia UTF-8 de "ó") | Pérdida del centrado métrico y de los márgenes específicos de las canciones líricas tradicionales. |

## **Especificaciones del Motor de Parsing: Diccionario Python e Heurísticas BeautifulSoup**

Para la ingestión, normalización y conversión automática de grandes volúmenes de libros electrónicos, se ha diseñado e implementado una arquitectura de código capaz de analizar el DOM del documento, identificar de forma heurística estructuras poéticas e instrumentar la reconstrucción semántica y de codificación8.

### **Métrica de Desviación de Indentación Líquida**

Para evaluar de manera analítica si un bloque de versos se comportará correctamente en dispositivos de lectura con tipografía de escala dinámica, se formula la relación de desborde de línea poética líquida mediante la siguiente ecuación:  
![][image2]  
Donde:

* ![][image3] representa la anchura horizontal real disponible para el renderizado del texto sin provocar desbordamientos1.  
* ![][image4] es la anchura total de la ventana gráfica o pantalla del dispositivo lector.  
* ![][image5] y ![][image6] representan las propiedades de margen y padding izquierdo del bloque de párrafo contenedor de la línea34.  
* ![][image7] es el valor negativo asignado a la propiedad CSS text-indent (responsable de la sangría de flujo)3.

Un marcado se evalúa como óptimo y resiliente bajo la relación analítica:  
![][image8]  
Esto asegura que el desborde secundario de un verso largo jamás colisionará con los límites físicos izquierdos de la pantalla, manteniendo en todo momento la legibilidad y la estructura rítmica del poema1.

### **Implementación del Script de Parsing en Python:**

Python  
import re  
import math  
from bs4 import BeautifulSoup, Comment

\# Diccionario Global Unificado de Mapeo y Normalización  
DICCIONARIO\_MAPEO\_LIRICO \= {  
    "containers": \[  
        "poema", "poesia", "poetry", "poem", "poem-rw", "poetry-container",
        "bloque-lirico", "calibre\_poetry", "vellum-verse-container", "prh-poetry-block",  
        "poes-a", "poes\\u00c3\\u00ada", "poes\\u00e3a", "drama-verse-play", "cup-poetry-container"  
    \],  
    "stanzas": \[  
        "estrofa", "stanza", "v-stanza", "line-group", "verse-block",
        "prh-stanza", "stanza-rw", "speech-line-group", "estrof-", "estrof\\u00e3",  
        "pt-stanza"  
    \],  
    "lines": \[  
        "verso", "verse-line", "line", "v-verse-line", "calibre1", "calibre2",
        "vellum-verse-line", "prh-line", "v-line", "l", "Poesia\_Verso\_Normal",  
        "pt-original-verse", "pt-translated-verse"  
    \],  
    "indents": \[  
        "i1", "i2", "i3", "indent-1", "indent-2", "sangria-1", "sangria-2",
        "vellum-verse-indent", "Poesia\_Verso\_Sangrado", "prh-verse-indent-1"  
    \],  
    "corruptions": {  
        "poes-a": "poesia",  
        "poes\\u00c3\\u00ada": "poesia",  
        "poes\\u00e3a": "poesia",  
        "sangr-a": "sangria",  
        "sangr\\u00c3\\u00ada": "sangria",  
        "estrof-": "estrofa",  
        "estrof\\u00e3": "estrofa",  
        "canci-n": "cancion",  
        "canci\\u00c3\\u00b3n": "cancion"  
    }  
}

class MotorForenseLirico:  
    def \_\_init\_\_(self, xhtml\_content):  
        self.soup \= BeautifulSoup(xhtml\_content, "xml")

    def corregir\_mojibake\_clases(self):  
        """  
        Localiza clases con distorsiones de codificación en el DOM   
        y las sustituye de manera sistemática por sus contrapartidas correctas.  
        """  
        for element in self.soup.find\_all(class\_=True):  
            clases\_nuevas \= \[\]  
            for clase in element\["class"\]:  
                clase\_corregida \= clase  
                for patron\_corrupto, reemplazo in DICCIONARIO\_MAPEO\_LIRICO\["corruptions"\].items():  
                    if patron\_corrupto in clase:  
                        clase\_corregida \= reemplazo  
                clases\_nuevas.append(clase\_corregida)  
            element\["class"\] \= clases\_nuevas  
        return self

    def es\_contenedor\_poetico\_heuristico(self, tag, umbral\_densidad=0.7):  
        """  
        Aplica reglas heurísticas de densidad sobre un elemento del DOM para evaluar  
        si contiene una estructura poética, basándose en la coincidencia de clases  
        o el ratio de versos/bloques de texto.  
        """  
        \# Regla 1: Coincidencia directa con los nombres del diccionario  
        clases \= tag.get("class", \[\])  
        if any(cl in clases for cl in DICCIONARIO\_MAPEO\_LIRICO\["containers"\]):  
            return True  
              
        \# Regla 2: Evaluación por densidad estructural  
        hijos\_parrafo \= tag.find\_all(\["p", "span"\], recursive=False)  
        if not hijos\_parrafo:  
            return False  
              
        coincidencias\_verso \= 0  
        for hijo in hijos\_parrafo:  
            clases\_hijo \= hijo.get("class", \[\])  
            \# Coincidencia por clase o existencia de saltos internos \<br/\> con texto corto  
            if any(cl in clases\_hijo for cl in DICCIONARIO\_MAPEO\_LIRICO\["lines"\]):  
                coincidencias\_verso \+= 1  
            elif hijo.find("br") and len(hijo.get\_text()) \< 100:  
                coincidencias\_verso \+= 1  
                  
        densidad \= coincidencias\_verso / len(hijos\_parrafo)  
        return densidad \>= umbral\_densidad

    def depurar\_malas\_practicas(self, container\_tag):  
        """  
        Identifica y limpia anomalías visuales como espacios duros iniciales,  
        caracteres Unicode vacíos y acumulaciones de saltos de línea consecutivos.  
        """  
        \# Eliminar comentarios vacíos inyectados por suites automáticas  
        for comment in container\_tag.find\_all(text=lambda text: isinstance(text, Comment)):  
            comment.extract()

        \# Limpiar espacios duros iniciales en elementos de texto de verso  
        for line in container\_tag.find\_all(\["p", "span"\]):  
            texto \= line.get\_text()  
            if texto:  
                \# Expresión regular que detecta espacios y secuencias Unicode de espacios invisibles  
                texto\_limpio \= re.sub(r"^\[\\s\\u2002\\u2003\\u2009\\u00a0\]+", "", texto)  
                if line.string:  
                    line.string \= texto\_limpio  
                else:  
                    \# Si tiene elementos hijos anidados, se limpia el primer nodo de texto  
                    first\_text \= line.find(text=True)  
                    if first\_text:  
                        first\_text.replace\_with(re.sub(r"^\[\\s\\u2002\\u2003\\u2009\\u00a0\]+", "", first\_text))

        \# Eliminar elementos \<br/\> redundantes consecutivos de separación estrofica  
        br\_consecutivos \= container\_tag.find\_all("br")  
        for br in br\_consecutivos:  
            siguiente \= br.next\_sibling  
            while siguiente and (siguiente.name \== "br" or (isinstance(siguiente, str) and not siguiente.strip())):  
                if siguiente.name \== "br":  
                    siguiente.extract()  
                siguiente \= br.next\_sibling

        return self

    def normalizar\_arbol\_semantico(self):  
        """  
        Estructura el documento aplicando de forma estricta el estándar EPUB 3,   
        encapsulando estrofas en párrafos de tipo estructural y líneas de verso en spans.  
        """  
        self.corregir\_mojibake\_clases()  
          
        for elem in self.soup.find\_all(\["div", "blockquote", "section"\]):  
            if self.es\_contenedor\_poetico\_heuristico(elem):  
                self.depurar\_malas\_practicas(elem)  
                  
                \# Re-etiquetado del elemento contenedor principal  
                elem.name \= "blockquote"  
                elem\["epub:type"\] \= "z3998:verse"  
                elem\["role"\] \= "doc-poem"  
                  
                \# Consolidación de estrofas basadas en párrafos  
                for p\_tag in elem.find\_all("p", recursive=False):  
                    p\_tag\["class"\] \= \["v-stanza"\]  
                    p\_tag.attrs.pop("id", None) \# Eliminar identificadores automáticos basura  
                      
                    \# Envolver las líneas de verso si eran planos  
                    text\_content \= p\_tag.get\_text().strip()  
                    if text\_content and not p\_tag.find("span"):  
                        \# Si no tiene spans pero sí br's, reconstruye a spans semánticos  
                        versos \= \[v.strip() for v in re.split(r"\<br\\s\*/?\>", str(p\_tag)) if v.strip()\]  
                        p\_tag.clear()  
                        for v in versos:  
                            span\_v \= self.soup.new\_tag("span")  
                            span\_v\["class"\] \= \["v-line"\]  
                            span\_v.string \= v  
                            p\_tag.append(span\_v)  
                            p\_tag.append(self.soup.new\_tag("br"))  
                        \# Eliminar el último break inyectado  
                        if p\_tag.contents and p\_tag.contents\[-1\].name \== "br":  
                            p\_tag.contents\[-1\].extract()  
                              
        return self.soup.prettify()

## **Conclusiones Forenses e Implicaciones para la Normalización**

El análisis forense de la maquetación digital de versos y poesía demuestra una fragmentación estructural severa dentro de la industria editorial internacional6. Mientras que las iniciativas de preservación y las prensas académicas de primer nivel aplican metodologías semánticas con un profundo conocimiento de los lenguajes XML y de la accesibilidad universal, el sector comercial masivo y la autoedición se ven sometidos a las limitaciones impuestas por los motores automáticos de exportación de las suites de diseño y software propietario3.  
La adopción de "hacks" visuales para simular en pantallas pequeñas el diseño estático del libro en papel destruye la flexibilidad semántica indispensable para la longevidad del libro digital1. Solo mediante la aplicación de rutinas heurísticas y el procesamiento automatizado mediante sistemas integrados basados en el DOM será posible recuperar la intencionalidad estructural del verso y asegurar una lectura digital estable, accesible y respetuosa con el ritmo impuesto por el autor en la obra1.

### **Obras citadas**

1. How to format a book of Poetry in MS Word (free tutorial\!) \- DIY Book Formats, [https://diybookformats.com/poetrybook/](https://diybookformats.com/poetrybook/)  
2. Books without Barriers: A Practical Guide to Inclusive Publishing, [https://digitalcommons.unl.edu/context/scholcom/article/1340/viewcontent/Bookswithoutbarriers\_Print.pdf](https://digitalcommons.unl.edu/context/scholcom/article/1340/viewcontent/Bookswithoutbarriers_Print.pdf)  
3. 7\. High Level Structural Patterns \- The Standard Ebooks Manual, [https://standardebooks.org/manual/1.0.0/7-high-level-structural-patterns](https://standardebooks.org/manual/1.0.0/7-high-level-structural-patterns)  
4. G1:Poetry: IGP:FoundationXHTML, [http://apex.infogridpacific.com/fx/fx-g1-poetry.html](http://apex.infogridpacific.com/fx/fx-g1-poetry.html)  
5. Indesign Reflowable Epub \- paragraph spacing issue \- Adobe Community, [https://community.adobe.com/questions-671/indesign-reflowable-epub-paragraph-spacing-issue-888078](https://community.adobe.com/questions-671/indesign-reflowable-epub-paragraph-spacing-issue-888078)  
6. Well Hung: Poetry, Ebooks, and Indents, Part One \- EPUBSecrets, [https://epubsecrets.com/well-hung-poetry-ebooks-and-indents-part-one.php](https://epubsecrets.com/well-hung-poetry-ebooks-and-indents-part-one.php)  
7. 7\. High Level Structural Patterns \- The Standard Ebooks Manual of Style, [https://standardebooks.org/manual/1.8.7/7-high-level-structural-patterns](https://standardebooks.org/manual/1.8.7/7-high-level-structural-patterns)  
8. How to Prepare a Gutenberg Text for Ereading (Step-by-Step) \- LifeTips, [https://lifetips.alibaba.com/tech-efficiency/prepare-a-gutenberg-text-for-ereading](https://lifetips.alibaba.com/tech-efficiency/prepare-a-gutenberg-text-for-ereading)  
9. Help on Download Options and Bibliographic Record \- Project Gutenberg, [https://www.gutenberg.org/help/bibliographic\_record.html](https://www.gutenberg.org/help/bibliographic_record.html)  
10. standardebooks/manual: The source code for the Standard Ebooks Manual of Style. · GitHub, [https://github.com/standardebooks/manual](https://github.com/standardebooks/manual)  
11. How HTML changes in ePub \- HTMHell, [https://www.htmhell.dev/adventcalendar/2025/11/](https://www.htmhell.dev/adventcalendar/2025/11/)  
12. Appendix: Restricted Procurement of EPUB 3.0 Production Services Requirements for Quality Content Production in EPUB 3.0/XHTML, [https://format.mtm.se/nordic\_epub/2015-1/nordic\_guidelines\_epub3-2015-1.pdf](https://format.mtm.se/nordic_epub/2015-1/nordic_guidelines_epub3-2015-1.pdf)  
13. The Standard Ebooks Manual of Style \- Standard Ebooks: Free and liberated ebooks, carefully produced for the true book lover, [https://standardebooks.org/manual/1.3.1/single-page](https://standardebooks.org/manual/1.3.1/single-page)  
14. Open Access e Documentazione Esami (con materiali ad accesso aperto) \- Servizio Bibliotecario di Ateneo \- Unicas, [https://www.unicas.it/sba/biblioteca-di-area-umanistica-giorgio-aprea/risorse/open-access-e-documentazione-esami-con-materiali-ad-accesso-aperto/](https://www.unicas.it/sba/biblioteca-di-area-umanistica-giorgio-aprea/risorse/open-access-e-documentazione-esami-con-materiali-ad-accesso-aperto/)  
15. Vellum strips paragraph spacing when applied to every paragraph, am I doing something wrong? : r/selfpublish \- Reddit, [https://www.reddit.com/r/selfpublish/comments/1qmyqxe/vellum\_strips\_paragraph\_spacing\_when\_applied\_to/](https://www.reddit.com/r/selfpublish/comments/1qmyqxe/vellum_strips_paragraph_spacing_when_applied_to/)  
16. Bridget Williams Books Catalogue: July 2012 \- July 2013 | PDF | Māori People \- Scribd, [https://www.scribd.com/document/113337652/Bridget-Williams-Books-Catalogue-July-2012-July-2013](https://www.scribd.com/document/113337652/Bridget-Williams-Books-Catalogue-July-2012-July-2013)  
17. Editio Self-Publishing discussion substituting cover in an epub file \- Goodreads, [https://www.goodreads.com/topic/show/683768-substituting-cover-in-an-epub-file](https://www.goodreads.com/topic/show/683768-substituting-cover-in-an-epub-file)  
18. We All Float Down Here \- EPUBSecrets, [https://epubsecrets.com/we-all-float-down-here.php](https://epubsecrets.com/we-all-float-down-here.php)  
19. G01:Poetry Selectors: IGP:FoundationXMTL, [http://apex.infogridpacific.com/fx/fx-g1-poetry-selectors.html](http://apex.infogridpacific.com/fx/fx-g1-poetry-selectors.html)  
20. Investigating the Remediation of Poetry through Critical and Creative Practice \- Newcastle University Theses, [https://theses.ncl.ac.uk/jspui/bitstream/10443/5900/1/Hebden%20P%20A%202023.pdf](https://theses.ncl.ac.uk/jspui/bitstream/10443/5900/1/Hebden%20P%20A%202023.pdf)  
21. InDesign to EPUB: Controlling content order \- Cari Jansen, [http://carijansen.com/moving-print-publications-to-epub/](http://carijansen.com/moving-print-publications-to-epub/)  
22. ShakesVision/PoetryJustification: Demo of a snippet I made to dynamically convert and show justified poetry \- specially for Urdu. · GitHub, [https://github.com/ShakesVision/PoetryJustification](https://github.com/ShakesVision/PoetryJustification)  
23. Vellum review: App offers a sleeker way to build ebooks | Macworld, [https://www.macworld.com/article/222662/vellum-review-app-offers-a-sleeker-way-to-build-ebooks.html](https://www.macworld.com/article/222662/vellum-review-app-offers-a-sleeker-way-to-build-ebooks.html)  
24. Jump in the Convertible: Ebook Conversion Tools \- davidkudler, [https://davidkudler.livejournal.com/75601.html](https://davidkudler.livejournal.com/75601.html)  
25. Ebook themes : r/Calibre \- Reddit, [https://www.reddit.com/r/Calibre/comments/of4bke/ebook\_themes/](https://www.reddit.com/r/Calibre/comments/of4bke/ebook_themes/)  
26. Indesign Reflowable Epub \- paragraph spacing issue \- Reddit, [https://www.reddit.com/r/indesign/comments/1aqxuh8/indesign\_reflowable\_epub\_paragraph\_spacing\_issue/](https://www.reddit.com/r/indesign/comments/1aqxuh8/indesign_reflowable_epub_paragraph_spacing_issue/)  
27. turn off automatic justification, when left align justification is turned on. \- Scrivener for macOS, [https://forum.literatureandlatte.com/t/turn-off-automatic-justification-when-left-align-justification-is-turned-on/94250](https://forum.literatureandlatte.com/t/turn-off-automatic-justification-when-left-align-justification-is-turned-on/94250)  
28. E-book conversion — calibre 9.9.0 documentation, [https://manual.calibre-ebook.com/conversion.html](https://manual.calibre-ebook.com/conversion.html)  
29. Vellum Software Review: How to Use Vellum Book Formatting \- selfpublishing.com, [https://selfpublishing.com/vellum-software-review/](https://selfpublishing.com/vellum-software-review/)  
30. Vellum 2.1, [https://blog.vellum.pub/2018/01/vellum-2-1/](https://blog.vellum.pub/2018/01/vellum-2-1/)  
31. format font by paragraph for epub? : r/Calibre \- Reddit, [https://www.reddit.com/r/Calibre/comments/1aeiyrw/format\_font\_by\_paragraph\_for\_epub/](https://www.reddit.com/r/Calibre/comments/1aeiyrw/format_font_by_paragraph_for_epub/)  
32. The Power of CSS in eBooks \- eBookBuilders \- Professional Book Design & Publishing Support for Indie Authors, [https://ebookbuilderspro.com/css-in-ebooks/](https://ebookbuilderspro.com/css-in-ebooks/)  
33. HTML FAQ (old) \- Project Gutenberg, [https://www.gutenberg.org/attic/html\_faq.html](https://www.gutenberg.org/attic/html_faq.html)  
34. ebook-convert(1) — calibre — Debian buster, [https://manpages.debian.org/buster/calibre/ebook-convert.1.en.html](https://manpages.debian.org/buster/calibre/ebook-convert.1.en.html)  
35. Seeking Formatting Tips for Selfpublishing Poetry Ebooks \- Reddit, [https://www.reddit.com/r/selfpublishing/comments/malj10/seeking\_formatting\_tips\_for\_selfpublishing\_poetry/](https://www.reddit.com/r/selfpublishing/comments/malj10/seeking_formatting_tips_for_selfpublishing_poetry/)

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,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>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC8AAAAaCAYAAAAnkAWyAAABoklEQVR4Xu2WPShFYRjHH/KZkEgpkQEpiwyKsJJQZJHBR8pHFllYKJOFiJKVwSRiUEJRBiETme5CGZRBCAP/p/d/ndN72e5w3jq/+nWej/fe+573vOecKxISEuIs4/D7H4t84wLNKHyCdTDP6gWeCOy1iy5QJmabFNoNFxgSM3kn2RJHJ98g3tPFOabFTPzabpBbmGgXg8KpmMnP2w2ybBeCQg78EjP5dqunJMNquxgUVsRM/Ih5CayFbfCKvSgtsBve+2o3PE7BR8YL8A7uwgz4yXoC3ISDMBu+wmH2cuEl3Bdvi/bxGEOpxP4V+MuP6AdAq5grsci8QLyT0/oJ4w7WG5n38Dgg5g2uY/M5ppI9PRndAU3MlVVfHBd0heoZd8FnxhVwhrHyBlN8uXIGNxh3wgdfrxm+w3TmaXDSa8cHXZlUxnNwj7H+UDljZdsXR3mBY4z16q3DTDFXSL9Lt0wUvf+KfXlcqBFvRQ/ETDILzv6OMExYuXIBRxhHxJxwP6yC53CHPV2cQ8ZOoPdWkl10hWO74AprYh6/S3YjJCRO/AAqaFboKc2cnwAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEwAAAAaCAYAAAAdQLrBAAAC10lEQVR4Xu2YWahNURjH/6bMU4aSBw/m4UVmhZsh05OxdB9ExpIoSURCJLMHUShDSYqQeDCkhIQHSTxdIfFCEoXE/9/3rfY664brPpw4e//q11n7+849e+81rwsUFBQUFOSO0/RHomhL3yfxz3So548muRMezwUvYS+9JU2QybDceNo0ijeiY+l32os2iHIVz0VYpRxKE2QvLDcsibemD2mnJJ4LjsEqRcMzZjhd5LkpSW4fnZ/EcsNuWKVcjWIaYgf9U7m5Ua6KXo+uc8daWKU8iGJL6GAvK7cqyj2m/aPr3DEdVilf/HojbI4KxPPbQNosytWFHrQGtkhUBFXItgdt6MySrMXPePlKnKgjXelhlDbCv4LeV8/3VwxAVmHdkpxQ/BpdBnvxSmIObZIG/0QXZBW2IckJxV/Rp7RjkvvfOZIG6so7+pq2TBOovYKmHKcdYJtY7dcO0Eue20Z30gt+LXSfrdF1Q7qZ9oSt2KIV/UonwObPe7DG2g57nrDNGURbePkkPeXlxfQRbLjNhv2N5tDVsA4ienu8Xtym89Kg8wS/H+d96FL6DPbyqrQdnptBX9CFfi30IjopiO7+OYs2hp06xET6DVZxOkno6NWX9kPpaj6CDoHtCXV0U8OJSbDKGEd30VseD/cT2mO+ja7Lyh1klaQH0VEqoBdp5+X29CZdT1fS6vAlMhX2XaEep0YUevkFXhbqtQHNq53pXXouiq+BVZjuq965KcoF1AihR5YVrX56OPUKcR7W0wI6qGsroiGhQ/20KBejlwo9QUM6NMAeWEULTRmqwMBl/3xD10Vx/Y7uK9RTx0S5wHNYz9fvhQYtC1plPiF7qPgY1ZyOpsthq7GIh742x2GVWkFvwOakGmTznHpiQP8M0O+JkfSDl8/S/V7W76jHh23MR9TeO6oB1Mi6v+bciuV+Gij4NVol672q5Q0Ndw0zVdioJFdQUJA/fgJRtZQTV6gCzgAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC4AAAAaCAYAAADIUm6MAAACK0lEQVR4Xu2Vz4uNYRTHv36l5HdNNGWhFJE04g8YspKhLJQFshFKSbKYSVmwmEJkR4SkZiyUFJGFwkI2FKIQSn4sbCyMBd+vc97mvOdet9nMfa96P/Wt55zv0+3c5znPeYGampr/gi3U76A7ZbuBUyjvP1q22896WCGvspG4Dtv3nlqZvEq4Sz2DFbUseQUHqaewPZuSVwkzqM/UDVhROv3MUmonzP9FzS7b1dBHDVFnYIXtKduYSB33tfyHwauUk9RuWCuosMGyjQPUIl/LPxa8yuim3vq6B1bYY48nU+epSR4vhrXJNI/FYeoH9SbkxkI/dZG6mY2xor496+vpsMK/e7yfWu5rsZe6FeKCy9S1nGyB3tBrWGtqIBTMoZ6EuCVXqK0h/gQrvgvWIhEVp3bKfEDj3lZcos5Rs6iZIb+N+hLif6JH95WaH3L3YYWvpqaE/ATqG6ydImof7c/5VnxE4wAQap2rOZlR/2r86YOzCvYnxACskCMeF5zwvN5ERDd2IcTa945a4PG+UesvG2C/oxEc0bdD+SUpX2IebFOU+lSsg/XZVNisHmmy94HvFTq97SGWv9nXOgzdSOQQ9SLlhN6PWq5tqNCFIf4JG5e6uV0hX6B20C1llFPvt42XsP7XR0w8Cl4zNEWaPXDd3A5fx3E7bugE12B0qjyH/RGhdtvo6wLdUG/KzfX8CpSnTEeggvSwh7PR6aiFblNrs9HpnKbu5WRNzTjwB9K7dPlfAhv1AAAAAElFTkSuQmCC>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACcAAAAaCAYAAAA0R0VGAAABsklEQVR4Xu2VOSwFURSGj100iCXWvEpHJ0pe9AqFCBGis0WJSBQKlaUWsSWEwtKLSqNQKkREQqgsnQoR/pNzJ3OdN++9kZdcEvMlX3Lv+d+bOXeWO0QRERFJGYGfKbyBszDX+8NvMEzSTJGqr5r6AcxWmTMuSJrQxMi/iuMqc0It+Q1oRsnPWlTmhH6Sk5/oAFyRZJuq7owtkgamrFohbIMfcA7mWJkzmkkae4UFKrPpgI+wXgdp6IFnsFwHYZgkae5YBwHwG/0T6uA7fIZVVp0bLbbmSTkiaW5GBwFs60IaxuA5rFb1QZilagnwbXwjaS7+PQrkQRfSsA/XdJFCLnKepLFTHQTAX5JLa95JsrB22ECJbzPfOj425zZNpp6UGPl7l619cs0uXDbjEvgEl8x8CHaZsUec5Jhlqs775p2qZQzf0j4z5qvGJ94geVZbvR9Z8MtzrYtgB67rYiY0kjRTY+Zec/o7bLMC93QR3MMBkmOk2rpC00tyFUrNvBK+kN8sP48TZuzBe5u9qTMVJIvixS6qzAl5JN/gWwqxXbhmgWRjn9bBX6AbHsJ8HUT8W74AF2JbxYr2ZdQAAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADcAAAAaCAYAAAAT6cSuAAACN0lEQVR4Xu2WS4hOYRjH/0xqogZDIreRptmYXJIkGbks3a2YJqYmTckCyX2lFEVEbiu3ZjPRLGZhoaampFhMUlY0RUkWlGIl/v+e53TOPIk5zXzTN3p/9et7z/O+5znnPe/le4FEIpEYZSbRXyXssNvGBzvpdbqBNtAa5B1ZkzfDTY+tK8Sqmlr6KQZhnbgdYrPpuxCranbQByE2Eda5PSHeQntCrKpZSOeF2EpY5zRSRWbQphAbdxyjAzH4PzCZ/qDbY0WBJXQwBofJW1h+bVpjjnZMTckpsaJAA70Rg8PkDu2PwZLU05f+W4ozsM5Vilf0fAyWZB9sh9fGV4o+VLZzyr0xBktyn3bF4N+YQA/CHv4z1GVcgO2uV2HJF9BztJV+h62jOlgO7bjiMn0GW8visf+KbbBlIJRLOe/R+bAcvV73nB72crPXNfr1P3mP/EQSnV5op5OMjmof6V66AvaQK/Spt1kOu08vu8zLq71OZC85DUMPD+2wnJvobvqVToV99M+0zdtpAPS+FWEL/QI72WRoHR338gnYYhcX6QcvC/1PZiOqw4M6rjXeSdd7XFxDPmprYe1m+vVDetfLo46S6xyq6SfmwB7e4tdv6CnYyD2i3R4Xu2BTVx8o69yfeE1Pe/kWfQIbQd2jUdvvdVsx9COPCK0brcdV9IjHNJW+wabrYtgLazqepZeQL3ytoxd0ET1KZ8HuyzhAT9K5sBzZgV3/i4foZuQfZClsyip/IpFIJEbEb/pVdMOqO1N1AAAAAElFTkSuQmCC>

[image8]: <data:image/png;base64,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>
