# **Informe de Investigación: Ingeniería Inversa y Normalización Estructural de Notas al Pie en Archivos EPUB para Pandoc**

El procesamiento automatizado de libros digitales mediante herramientas de conversión como Pandoc requiere una homogeneidad estructural estricta en el marcado de los documentos de entrada. No obstante, el ecosistema de la edición digital se caracteriza por una amplia dispersión en los métodos de generación de XHTML, donde cada motor de maquetación implementa una jerarquía de Document Object Model (DOM) particular para las notas al pie. La presente investigación detalla los patrones estructurales de los doce motores de exportación más utilizados en la industria, analizando su arquitectura semántica en entornos EPUB 2 y EPUB 3, con el objetivo de servir como especificación técnica para el desarrollo de una herramienta de normalización basada en el patrón de diseño *Strategy* y la biblioteca BeautifulSoup de Python.

## **1\. El mapa de herramientas de generación de EPUB**

Para diseñar un pipeline de normalización robusto, es indispensable clasificar las herramientas de generación según su origen técnico y la naturaleza de su salida. Los motores analizados se dividen en cuatro categorías fundamentales:

* **Entornos de diseño profesional (Desktop Publishing \- DTP):** Plataformas que priorizan el control visual y tipográfico complejo, generando estructuras DOM altamente jerarquizadas y dependientes de clases CSS internas de maquetación1.  
* **Editores de EPUB dedicados:** Herramientas concebidas específicamente para la manipulación directa del código de libros digitales, garantizando un marcado limpio y apegado a las especificaciones oficiales del consorcio W3C1.  
* **Convertidores automáticos:** Procesadores por lotes y complementos que traducen formatos de procesadores de texto de escritorio (como DOCX) a paquetes EPUB, aplicando heurísticas internas para simular la semántica del libro impreso4.  
* **Plataformas de publicación web (Web-to-EPUB):** Entornos de gestión de contenido basados en tecnologías de servidor que exportan bases de datos HTML a formatos de empaquetado digital reflowable7.

La siguiente tabla resume la clasificación, el enfoque de maquetación y la especificación de salida predominante para cada una de las herramientas de software investigadas.

| Herramienta / Motor de Generación | Clasificación de Plataforma | Enfoque de Maquetación | Especificación de Salida Predeterminada |
| :---- | :---- | :---- | :---- |
| **Adobe InDesign** | Diseño Profesional (DTP) | Estilos tipográficos rígidos y herencia visual de clases1 | EPUB 3 (XHTML5) / EPUB 2 (XHTML 1.1)9 |
| **Sigil (footnote-gen)** | Editor de EPUB Dedicado | Edición de código a bajo nivel y control directo del DOM1 | EPUB 3 (XHTML5) semántico y limpio10 |
| **Calibre (convert)** | Convertidor Automático | Reescalado dinámico de tipografías y aplanamiento de clases1 | Estructuras simplificadas basadas en clases de motor4 |
| **Jutoh** | Editor de EPUB Dedicado | Compilación de múltiples formatos optimizada por plantillas12 | EPUB 3 semántico y EPUB 2 compatible13 |
| **Vellum** | Diseño Automatizado | Plantillas visuales optimizadas para tiendas específicas14 | EPUB 3 optimizado para pop-ups2 |
| **Atticus** | Diseño Automatizado | Edición WYSIWYG multiplataforma en la nube14 | EPUB 3 estándar para Amazon KDP16 |
| **Reedsy Studio** | Plataforma Web-to-EPUB | Exportación simplificada para flujos de distribución directa8 | EPUB 3 limpio con CSS consolidado17 |
| **Pressbooks** | Plataforma Web-to-EPUB | Basado en el motor de WordPress y compilación de shortcodes7 | EPUB 3 basado en la semántica del tema7 |
| **Apple Pages** | Procesador de Texto / Exportador | Conversión directa de documentos de procesamiento de palabras20 | EPUB 3 adaptativo con conversión de notas20 |
| **Kindle Create** | Convertidor Automático | Preparación y conversión propietaria para Amazon KDP21 | KPF / EPUB 3 adaptado para dispositivos Kindle22 |
| **DAISY WordToEPUB** | Convertidor Automático | Alta accesibilidad y cumplimiento estricto de WCAG5 | EPUB 3 con marcado semántico extendido5 |
| **Pandoc** | Convertidor Multiformato | Conversión basada en Árboles de Sintaxis Abstracta (AST)26 | EPUB 3 semántico optimizado para accesibilidad27 |

## **2\. Huellas estructurales de DOM para notas al pie**

A continuación, se presenta un análisis exhaustivo del marcado generado por cada una de las doce herramientas listadas, centrándose exclusivamente en la estructura del DOM, los atributos clave de los enlaces y elementos de bloque, y la lógica de bidireccionalidad.

### **2.1. Adobe InDesign**

* **La llamada (Callout):** La referencia se estructura mediante un enlace a que posee el atributo semántico epub:type="noteref". Este enlace se encuentra envuelto de forma común directamente en el párrafo de texto, a menudo acompañado de clases autogeneradas con el prefijo \_idGen o nombres asociados a estilos de carácter específicos28.  
* **El cuerpo de la nota (Footnote Body):** En flujos de trabajo EPUB 3 reflowable, el cuerpo de la nota se almacena en un elemento semántico \<aside\> con el atributo epub:type="footnote" y la clase \_idFootnote28. InDesign posiciona este contenedor de manera intercalada inmediatamente después del párrafo donde ocurre la llamada, lo cual permite la activación de ventanas emergentes interactivas en sistemas de lectura compatibles como Apple Books9.  
* **El enlace de retorno (Backlink):** InDesign genera un enlace de anclaje vacío con el atributo id asignado a la nota, como \<a class="\_idFootnoteAnchor" href="..."\>\</a\>28. El enlace se sitúa justo antes del texto explicativo de la nota, utilizando el atributo href para apuntar de vuelta a la llamada.  
* **Variación EPUB 2 vs. EPUB 3:** En la exportación a EPUB 2, InDesign elimina el elemento \<aside\> y despoja el código de los atributos epub:type28. El cuerpo de la nota se transforma en un párrafo convencional \<p class="Footnotes"\> o en una lista de ítems agrupados al final de la sección o del capítulo9.

HTML  
\<\!-- LLAMADA \--\>  
\<p class\="Texto\_Normal"\>  
  La teoría cosmológica propuesta en esta obra revolucionó la física clásica.\<a class\="\_idFootnoteLink \_idGenColorInherit" epub:type\="noteref" href\="chapter1.xhtml\#footnote-201-backlink" id\="footnote-201"\>1\</a\>  
\</p\>

\<\!-- CUERPO DE LA NOTA \--\>  
\<aside id\="footnote-201-backlink" class\="\_idFootnote" epub:type\="footnote"\>  
  \<p class\="Alineacion\_Nota"\>\<a class\="\_idFootnoteAnchor \_idGenColorInherit" href\="chapter1.xhtml\#footnote-201"\>\</a\>1\. Galileo Galilei, \<em\>Sidereus Nuncius\</em\>, 1610\.\</p\>  
\</aside\>

**Patrón estructural abstracto:** Un elemento de anclaje a con el atributo epub:type="noteref"28, cuyo atributo id se vincula de manera directa y simétrica con el atributo href de un contenedor adyacente o hermano \<aside epub:type="footnote"\>28, el cual encierra un párrafo con un anclaje de retorno carente de contenido de texto28.

### **2.2. Sigil (plugin footnote-gen)**

* **La llamada (Callout):** Genera la llamada envolviendo un elemento de anclaje a en un superíndice sup31. El elemento a puede incluir la clase duokan-footnote si se activa el perfil de compatibilidad específico de lectura32.  
* **El cuerpo de la nota (Footnote Body):** Los cuerpos se recopilan tradicionalmente al final del archivo XHTML de la sección o en un documento independiente (notes.xhtml) dentro de una lista ordenada (ol) donde cada nota corresponde a un elemento de lista li con identificadores unívocos como fndef\_X32.  
* **El enlace de retorno (Backlink):** Cada ítem de la lista se inicia con un anclaje que contiene caracteres simbólicos preestablecidos (por ejemplo, ◎, ^ o el número de la nota) que redirige al identificador de la llamada en el cuerpo del texto32.  
* **Variación EPUB 2 vs. EPUB 3:** Para EPUB 3, se aplican atributos semánticos epub:type="noteref" en la llamada y epub:type="footnote" en el elemento contenedor li o en el bloque adyacente32. En EPUB 2, el plugin suprime estos atributos y se apoya exclusivamente en hipervínculos bidireccionales basados en el estándar XHTML 1.133.

HTML  
\<\!-- LLAMADA \--\>  
\<p class\="parrafo"\>El análisis textual arrojó discrepancias fundamentales.\<sup\>\<a class\="duokan-footnote" epub:type\="noteref" href\="\#fndef\_1" id\="fnanchor\_1"\>1\</a\>\</sup\>\</p\>

\<\!-- CUERPO DE LA NOTA \--\>  
\<ol class\="footnotes-list"\>  
  \<li class\="duokan-footnote-item" id\="fndef\_1"\>  
    \<p\>\<a class\="backlink" href\="\#fnanchor\_1"\>◎\</a\> 1\. Véase el apéndice crítico de transcripciones paleográficas.\</p\>  
  \</li\>  
\</ol\>

**Patrón estructural abstracto:** Un elemento de llamada a anidado directamente en un elemento sup31 con atributos de id numéricos, cuyo href apunta a un elemento li dentro de una lista ordenada terminal al final de la sección o capítulo32.

### **2.3. Calibre (convert)**

* **La llamada (Callout):** Calibre genera marcas hipervinculadas mediante el uso de etiquetas de anclaje a típicamente estilizadas con clases genéricas autogeneradas (calibre\_link o numeradas recursivamente, ej. calibre1, calibre2)11. El anclaje se encuentra dentro de un tag sup o hereda estilos en línea de tamaño de fuente4.  
* **El cuerpo de la nota (Footnote Body):** En procesos automatizados de conversión (p. ej., DOCX a EPUB), las notas se deponen en bloques div o párrafos p al final de cada archivo capitular4. La estructura de identificación carece frecuentemente de esquemas lógicos jerárquicos estándar, empleando patrones del tipo note\_X o footnote\_X.  
* **El enlace de retorno (Backlink):** Se genera un hipervínculo interno en el cuerpo de la nota con el texto representativo de una flecha hacia arriba (↑) o el número de nota encerrado en corchetes (\[1\]) que redirige al anclaje de origen37.  
* **Variación EPUB 2 vs. EPUB 3:** Si la configuración de conversión de salida de Calibre se fuerza a EPUB 2, se prescinde de todo atributo semántico33. Al exportar a EPUB 3, si el motor de conversión detecta la semántica original, añade de forma automatizada los roles ARIA correlativos: role="doc-noteref" en la llamada y role="doc-footnote" en el contenedor de llegada39.

HTML  
\<\!-- LLAMADA \--\>  
\<p class\="calibre12"\>La teoría de cuerdas propone múltiples dimensiones.\<sup\>\<a class\="calibre21" href\="cap1.xhtml\#note\_id\_1" id\="back\_id\_1"\>\[1\]\</a\>\</sup\>\</p\>

\<\!-- CUERPO DE LA NOTA \--\>  
\<div class\="calibre35" id\="note\_id\_1"\>  
  \<p class\="calibre40"\>\<a class\="calibre\_back" href\="cap1.xhtml\#back\_id\_1"\>↑\</a\> \<strong\>1\.\</strong\> Una explicación matemática de diez dimensiones se ofrece en el volumen dos.\</p\>  
\</div\>

**Patrón estructural abstracto:** Un enlace a cuyo atributo de clase coincide con la expresión regular ^calibre\[0-9\]+$11, contenido en una estructura tipográfica superior, cuyo href apunta a un elemento div terminal que aloja un retroenlace con el caracter Unicode ↑ (\&uarr;).

### **2.4. Jutoh**

* **La llamada (Callout):** Jutoh genera estructuras de notas al pie que dependen fuertemente de los estilos de caracteres mapeados por el usuario40. La llamada consiste en un enlace a que envuelve un número, opcionalmente estructurado dentro de un elemento sup para asegurar la correcta escala del elemento flotante en pantalla40.  
* **El cuerpo de la nota (Footnote Body):** Los cuerpos se procesan bajo la semántica de contenedores de bloque, usualmente empleando etiquetas \<aside\> en EPUB 3 con el atributo epub:type="footnote" o elementos de lista con clases estructuradas por el motor de diseño (jutoh-footnote)12.  
* **El enlace de retorno (Backlink):** El enlace de retorno está integrado al inicio del cuerpo de la nota mediante un anclaje directo sobre el número de nota o un marcador gráfico correlativo12.  
* **Variación EPUB 2 vs. EPUB 3:** En compilaciones EPUB 3, Jutoh aprovecha el espacio de nombres semántico (xmlns:epub) para inyectar de manera nativa los atributos epub:type13. En compilaciones EPUB 2, las notas son degradadas a hipervínculos bidireccionales basados en uniones tradicionales entre elementos a y marcadores de párrafo con estilos de sangría colgante personalizados12.

HTML  
\<\!-- LLAMADA \--\>  
\<p class\="Normal"\>La materia oscura compone gran parte del cosmos.\<a class\="Char-Style-Footnote-Anchor" href\="chapter2.xhtml\#footnote\_jutoh\_2" id\="callout\_jutoh\_2"\>\<sup\>2\</sup\>\</a\>\</p\>

\<\!-- CUERPO DE LA NOTA \--\>  
\<aside class\="Footnote-Section" id\="footnote\_jutoh\_2" epub:type\="footnote"\>  
  \<p class\="Footnote-Paragraph"\>\<a class\="Char-Style-Footnote-Return" href\="chapter2.xhtml\#callout\_jutoh\_2"\>2\.\</a\> Estimaciones astrofísicas sitúan su presencia en aproximadamente el 85% de la materia total.\</p\>  
\</aside\>

**Patrón estructural abstracto:** Un hipervínculo a con un estilo de carácter identificable en la clase de anclaje de Jutoh, que apunta a un bloque de nota \<aside\> con identificador formateado (^footnote\_jutoh\_\[0-9\]+$) o clase correlativa generada por el motor de Jutoh.

### **2.5. Vellum**

* **La llamada (Callout):** Vellum genera un código XHTML sumamente estilizado y optimizado para la lectura digital14. La llamada consiste en un enlace a con atributos dobles de accesibilidad de EPUB 3: epub:type="noteref" y role="doc-noteref"15. El número de llamada es presentado sin la etiqueta sup, manejando la tipografía de superíndice directamente mediante asignación de clases de CSS a nivel de la etiqueta a41.  
* **El cuerpo de la nota (Footnote Body):** El cuerpo se implementa bajo un elemento \<aside\> que incorpora de forma estricta los atributos semánticos epub:type="footnote" y role="doc-footnote"39. Se agrupan al final del archivo XHTML capitular para permitir el despliegue del pop-up en plataformas compatibles15.  
* **El enlace de retorno (Backlink):** Vellum incorpora retroenlaces bidireccionales integrados directamente en el número de nota dentro del contenedor \<aside\> para asegurar la usabilidad en dispositivos de tinta electrónica que no despliegan menús emergentes (p. ej., dispositivos Nook heredados o lectores genéricos)2.  
* **Variación EPUB 2 vs. EPUB 3:** Para versiones de EPUB 2, el compilador propietario de Vellum descompone la etiqueta \<aside\> en bloques div convencionales y elimina de forma total la semántica de la especificación EPUB 315.

HTML  
\<\!-- LLAMADA \--\>  
\<p class\="parrafo\_vellum"\>La tectónica de placas explica la deriva continental.\<a class\="vellum-noteref" epub:type\="noteref" href\="\#fn\_id\_3" id\="ref\_id\_3" role\="doc-noteref"\>3\</a\>\</p\>

\<\!-- CUERPO DE LA NOTA \--\>  
\<aside class\="vellum-footnote" id\="fn\_id\_3" epub:type\="footnote" role\="doc-footnote"\>  
  \<p class\="vellum-footnote-text"\>\<a class\="vellum-backlink" href\="\#ref\_id\_3"\>3\</a\> Alfred Wegener propuso la hipótesis original en 1912\.\</p\>  
\</aside\>

**Patrón estructural abstracto:** Un enlace de anclaje a que contiene exclusivamente dígitos numéricos, libre de anidamiento dentro de etiquetas sup, que cuenta simultáneamente con epub:type="noteref" y role="doc-noteref", apuntando a un bloque \<aside id="..."\> con los atributos semánticos homólogos de destino39.

### **2.6. Atticus**

* **La llamada (Callout):** En Atticus, la llamada se representa típicamente mediante un enlace a que envuelve un marcador numérico, anidado dentro de una etiqueta sup para forzar la visualización como superíndice en todas las pantallas de lectura14.  
* **El cuerpo de la nota (Footnote Body):** El cuerpo de la nota se almacena en una estructura de lista o bloque genérico al final del capítulo16. Debido a limitaciones en la madurez del motor, los identificadores y las rutas se generan de forma consecutiva pero simple (ej. atticus-footnote-X), siendo propensos a la ruptura de enlaces si se realiza una duplicación del volumen o sección41.  
* **El enlace de retorno (Backlink):** Cuenta con un enlace que utiliza el número de referencia del cuerpo para permitir la redirección inversa al texto base de lectura.  
* **Variación EPUB 2 vs. EPUB 3:** En las exportaciones a EPUB 3, el motor intenta incorporar los atributos semánticos del estándar actual. No obstante, en la exportación a EPUB 2, se limita a la escritura de una estructura tradicional de hipervínculos bidireccionales lineales entre anclajes del documento.

HTML  
\<\!-- LLAMADA \--\>  
\<p class\="atticus-body"\>El genoma humano contiene aproximadamente tres mil millones de pares de bases.\<sup\>\<a class\="atticus-fn-ref" href\="\#atticus-fn-12" id\="atticus-ref-12"\>12\</a\>\</sup\>\</p\>

\<\!-- CUERPO DE LA NOTA \--\>  
\<div class\="atticus-footnotes-wrapper"\>  
  \<div class\="atticus-footnote-item" id\="atticus-fn-12"\>  
    \<p class\="atticus-fn-text"\>\<a href\="\#atticus-ref-12" class\="atticus-back"\>12\.\</a\> Proyecto Genoma Humano, publicación de la secuencia completa en 2003\.\</p\>  
  \</div\>  
\</div\>

**Patrón estructural abstracto:** Un enlace a anidado bajo un tag sup con identificadores y clases que inician de manera invariable con el patrón atticus-16, apuntando a un contenedor div con la clase atticus-footnote-item.

### **2.7. Reedsy Studio**

* **La llamada (Callout):** El entorno de edición de Reedsy procesa la llamada mediante la inserción de un anclaje a dentro de una etiqueta de superíndice sup43. Su arquitectura de salida de código es sumamente limpia, orientada a superar con éxito la validación de EPUBCheck18.  
* **El cuerpo de la nota (Footnote Body):** El cuerpo de la nota se genera automáticamente y se consolida al final del capítulo correspondiente18 o se agrupa en un archivo de texto independiente de notas capitulares finales (endnotes.xhtml), dependiendo de la preferencia seleccionada en el menú de exportación de Reedsy Studio18.  
* **El enlace de retorno (Backlink):** Cuenta con un enlace bidireccional limpio utilizando el marcador numérico seguido de un punto y espacio dentro de la etiqueta contenedora de la nota.  
* **Variación EPUB 2 vs. EPUB 3:** Para el estándar EPUB 3, Reedsy Studio escribe anclajes semánticos con atributos del estándar8. En la configuración para EPUB 2 (heredado para sistemas antiguos), se prescinde de los atributos del espacio de nombres epub:type y se estructura un sistema puro de hipervínculos bidireccionales en formato HTML plano.

HTML  
\<\!-- LLAMADA \--\>  
\<p class\="reedsy-text"\>La fotosíntesis convierte la energía lumínica en energía química.\<sup\>\<a class\="reedsy-noteref" href\="endnotes.xhtml\#reedsy-note-1" id\="reedsy-anchor-1"\>1\</a\>\</sup\>\</p\>

\<\!-- CUERPO DE LA NOTA (Ubicado en endnotes.xhtml) \--\>  
\<div class\="reedsy-notes-list"\>  
  \<div class\="reedsy-note-body" id\="reedsy-note-1"\>  
    \<p\>\<a class\="reedsy-backlink" href\="chapter1.xhtml\#reedsy-anchor-1"\>1\.\</a\> Melvin Calvin describió el ciclo metabólico de fijación del carbono.\</p\>  
  \</div\>  
\</div\>

**Patrón estructural abstracto:** Un elemento de anclaje a contenido dentro de un elemento sup, cuyo href apunta de manera externa a un archivo de notas dedicado o a una sección final mediante identificadores con el prefijo estricto reedsy-8.

### **2.8. Pressbooks**

* **La llamada (Callout):** Derivada del procesamiento del shortcode \[footnote\] en la plataforma basada en WordPress19, la llamada se renderiza como una etiqueta a estilizada con la clase footnote y un ID autogenerado que combina la ID interna del post y el índice de aparición de la nota45.  
* **El cuerpo de la nota (Footnote Body):** Pressbooks agrupa los textos de las notas al pie de manera secuencial en una lista ordenada (ol) al final de cada capítulo XHTML19. El contenedor ol lleva el atributo semántico de accesibilidad de EPUB 3 role="doc-endnotes"27, y cada ítem de la lista li se marca con role="doc-endnote"27.  
* **El enlace de retorno (Backlink):** Cada elemento de la lista culmina con un enlace explícito que contiene el caracter especial Unicode de retorno de carro (↵) estilizado con la clase backlink47.  
* **Variación EPUB 2 vs. EPUB 3:** En EPUB 3, incorpora de manera impecable el marcado dual mediante atributos semánticos del estándar EPUB y roles DPUB-ARIA de accesibilidad27. En EPUB 2, estos se reducen a listas ordenadas puras y corrientes con enlaces relativos bidireccionales ordinarios.

HTML  
\<\!-- LLAMADA \--\>  
\<p class\="pressbooks-body"\>La paradoja de Fermi aborda la probabilidad de vida extraterrestre.\<a class\="footnote" href\="\#fn-152-1" id\="fnref-152-1"\>\<sup\>1\</sup\>\</a\>\</p\>

\<\!-- CUERPO DE LA NOTA \--\>  
\<ol class\="footnotes" role\="doc-endnotes"\>  
  \<li id\="fn-152-1" role\="doc-endnote"\>  
    \<p\>Enrico Fermi formuló la interrogante original en un almuerzo de trabajo en 1950\. \<a class\="backlink" href\="\#fnref-152-1" role\="doc-backlink"\>↵\</a\>\</p\>  
  \</li\>  
\</ol\>

**Patrón estructural abstracto:** Un enlace de anclaje a con la clase estricta footnote que apunta a un elemento li con el atributo role="doc-endnote" dentro de una lista ordenada \<ol class="footnotes" role="doc-endnotes"\>27, cuya conclusión posee un enlace de clase backlink que contiene exclusivamente el caracter ↵47.

### **2.9. Apple Pages**

* **La llamada (Callout):** Pages procesa la llamada a través de un enlace de anclaje a posicionado como superíndice de manera nativa mediante hojas de estilo incrustadas. Al exportar a EPUB, se remueven los campos inteligentes de Pages y las notas al pie se convierten de manera obligatoria a notas al final20.  
* **El cuerpo de la nota (Footnote Body):** El cuerpo de la nota se unifica en una sección XHTML independiente, colocada al final del manifiesto del EPUB20. Se codifica dentro de bloques div o listas de párrafos con clases identificadoras de estructura interna propietarias de Apple (apple-endnote)20.  
* **El enlace de retorno (Backlink):** Pages proporciona retroenlaces numéricos que vinculan el número correspondiente de la nota directamente con el anclaje de la llamada de origen dentro del archivo de cada capítulo20.  
* **Variación EPUB 2 vs. EPUB 3:** Para flujos de exportación configurados en EPUB 3, incorpora clases y puntos de navegación accesibles en el documento de navegación de EPUB (nav.xhtml) bajo los elementos semánticos recomendados (epub:type="endnotes")49. En EPUB 2, se remueve el archivo semántico de navegación y el marcado se descompone a XHTML 1.1 plano34.

HTML  
\<\!-- LLAMADA \--\>  
\<p class\="parrafo\_pages"\>La velocidad de la luz en el vacío es una constante física fundamental.\<sup\>\<a class\="pages-endnote-link" href\="endnotes.xhtml\#pages-fn-1" id\="pages-ref-1"\>1\</a\>\</sup\>\</p\>

\<\!-- CUERPO DE LA NOTA (Ubicado en el archivo endnotes.xhtml) \--\>  
\<div class\="apple-endnote-wrapper" id\="pages-fn-1" role\="doc-endnote"\>  
  \<p class\="pages-footnote-text"\>\<a class\="pages-return" href\="chapter1.xhtml\#pages-ref-1"\>1\.\</a\> Albert Einstein la estableció como pilar de la Relatividad Especial.\</p\>  
\</div\>

**Patrón estructural abstracto:** Un enlace de estilo superíndice (sup \> a) que posee una referencia externa (href) dirigida de forma invariable al archivo consolidado de destino final endnotes.xhtml y que hace uso de identificadores estructurados secuencialmente20.

### **2.10. Kindle Create**

* **La llamada (Callout):** Kindle Create procesa la llamada de nota a través de una jerarquía de etiquetado que envuelve al elemento a en un bloque sup30. El enlace se identifica mediante clases numéricas del motor de conversión KDP30.  
* **El cuerpo de la nota (Footnote Body):** En dispositivos de visualización modernos con soporte KF8 y EPUB 3, el cuerpo de la nota al pie se procesa mediante un bloque adyacente \<aside epub:type="footnote"\>30. De manera alternativa, el compilador genera un listado agrupado al final del capítulo22.  
* **El enlace de retorno (Backlink):** Incorpora un enlace de retorno de texto numérico directo (como 1.) al inicio de la nota, apuntando al anclaje superior de la llamada para asegurar la compatibilidad con dispositivos antiguos que carecen de sistema de previsualización emergente30.  
* **Variación EPUB 2 vs. EPUB 3:** Para flujos de lectura optimizados de EPUB 3, la integración semántica del elemento aside habilita el despliegue del pop-up flotante interactivo en pantallas táctiles30. En conversiones compatibles con Kindle heredados, el compilador reorganiza el marcado en elementos de bloque lineales tradicionales sin atributos epub:type30.

HTML  
\<\!-- LLAMADA \--\>  
\<p class\="kindle-text"\>El principio de exclusión de Pauli aplica a fermiones indistinguibles.\<sup\>\<a id\="kdp-ref-5" href\="\#kdp-fn-5" epub:type\="noteref"\>5\</a\>\</sup\>\</p\>

\<\!-- CUERPO DE LA NOTA \--\>  
\<aside id\="kdp-fn-5" epub:type\="footnote"\>  
  \<p class\="kindle-note"\>\<a href\="\#kdp-ref-5"\>5\.\</a\> Dos electrones en un átomo no pueden tener los mismos números cuánticos.\</p\>  
\</aside\>

**Patrón estructural abstracto:** Un enlace de llamada a con atributo de identificación propio encerrado en un elemento sup30, enlazado directamente a un elemento de bloque \<aside\> adyacente o al final de la sección con marcado semántico epub:type="footnote"30.

### **2.11. DAISY WordToEPUB**

* **La llamada (Callout):** Al ser una herramienta optimizada para la accesibilidad estructural, el anclaje incorpora atributos combinados robustos: class="noteref", epub:type="noteref" y role="doc-noteref"5.  
* **El cuerpo de la nota (Footnote Body):** El cuerpo se deposita de manera predeterminada dentro de una etiqueta \<aside\> que porta atributos semánticos de coincidencia doble: epub:type="footnote" y role="doc-footnote"5. El elemento se coloca inmediatamente después de la llamada o agrupado al final de la sección bajo un bloque accesible.  
* **El enlace de retorno (Backlink):** Incorpora un anclaje bidireccional accesible con el atributo role="doc-backlink", utilizando texto claro o el número correlativo para guiar a los lectores de pantalla de manera fluida5.  
* **Variación EPUB 2 vs. EPUB 3:** Al estar enfocado exclusivamente en la generación de especificaciones de alta accesibilidad modernas para EPUB 35, WordToEPUB no degrada por defecto a estructuras sin semántica, salvo que se fuerce la compatibilidad básica en cuyo caso los roles ARIA y atributos de accesibilidad son omitidos en el XHTML final5.

HTML  
\<\!-- LLAMADA \--\>  
\<p class\="Texto-Word"\>El cero absoluto representa el límite inferior de la temperatura.\<a class\="noteref" epub:type\="noteref" href\="\#daisy-fn-4" id\="daisy-ref-4" role\="doc-noteref"\>4\</a\>\</p\>

\<\!-- CUERPO DE LA NOTA \--\>  
\<aside class\="footnote" id\="daisy-fn-4" epub:type\="footnote" role\="doc-footnote"\>  
  \<p class\="Footnote-Text"\>\<a class\="backlink" href\="\#daisy-ref-4" role\="doc-backlink"\>4\.\</a\> Equivale a una temperatura de \-273,15 grados Celsius o cero Kelvin.\</p\>  
\</aside\>

**Patrón estructural abstracto:** Un enlace de anclaje a con la clase estricta noteref, portando concurrentemente los atributos epub:type="noteref" y role="doc-noteref", dirigido a un elemento de bloque \<aside\> que posee el rol doc-footnote39.

### **2.12. Pandoc**

* **La llamada (Callout):** Pandoc genera llamadas uniformes compuestas por un anclaje a con la clase footnote-ref y el rol role="doc-noteref"27. El número está siempre envuelto en la etiqueta de superíndice sup35.  
* **El cuerpo de la nota (Footnote Body):** Los cuerpos se recopilan estrictamente en la parte inferior del documento XHTML dentro de una sección semántica \<section class="footnotes" role="doc-endnotes"\>27. Cada nota individual se estructura como un elemento de lista li identificado por el patrón del ID correspondiente y el rol role="doc-endnote"27.  
* **El enlace de retorno (Backlink):** Cada elemento de la lista incluye un hipervínculo de retorno estilizado con la clase footnote-back y el rol role="doc-backlink", que utiliza de manera predeterminada el caracter Unicode de retorno de carro (↩)27.  
* **Variación EPUB 2 vs. EPUB 3:** Para versiones EPUB 3, Pandoc escribe la semántica completa de roles de accesibilidad27. En la conversión a EPUB 2, Pandoc sustituye la etiqueta \<section\> por un bloque genérico \<div\> y elimina todos los atributos role27.

HTML  
\<\!-- LLAMADA \--\>  
\<p\>El principio de incertidumbre de Heisenberg limita la precisión física.\<a class\="footnote-ref" href\="\#fn5" id\="fnref5" role\="doc-noteref"\>\<sup\>5\</sup\>\</a\>\</p\>

\<\!-- CUERPO DE LA NOTA \--\>  
\<section class\="footnotes" role\="doc-endnotes"\>  
  \<ol\>  
    \<li id\="fn5" role\="doc-endnote"\>  
      \<p\>Werner Heisenberg formuló el principio de incertidumbre de la mecánica cuántica en 1927\. \<a class\="footnote-back" href\="\#fnref5" role\="doc-backlink"\>↩\</a\>\</p\>  
    \</li\>  
  \</ol\>  
\</section\>

**Patrón estructural abstracto:** Un elemento de anclaje a de clase footnote-ref y rol doc-noteref27 que apunta de forma precisa a un ítem de lista li con el rol doc-endnote27 contenido dentro de un bloque superior \<section class="footnotes" role="doc-endnotes"\>27.

## **3\. Patrones anómalos y no estructurados (conversiones automáticas)**

Los procesos de conversión de baja calidad (como la conversión directa de archivos PDF de diseño fijo a EPUB fluido por lotes) a menudo rompen con toda jerarquía de marcado lógico53. Para robustecer el motor de normalización de BeautifulSoup, el programador debe implementar estrategias específicas para interceptar los tres patrones anómalos más comunes detectados en la industria.

### **3.1. Notas al pie intercaladas o "Inline"**

* **Descripción del problema:** Esta anomalía se genera cuando un motor de conversión simple procesa de forma lineal el texto de una página impresa en un PDF y, al llegar al final de la caja de texto visual de la página, inyecta el párrafo de la nota al pie directamente en el medio de una frase del flujo principal de lectura, interrumpiendo abruptamente la continuidad gramatical del párrafo de origen30.  
* **Huella digital de detección:** Se presenta estructuralmente como un elemento de párrafo p o bloque div que anida en su interior otro bloque o un párrafo secundario con un estilo tipográfico reducido, usualmente caracterizado por el uso de clases asociadas a fuentes más pequeñas o sangrías rígidas, rompiendo la continuidad del texto circundante.

HTML  
\<\!-- EJEMPLO DE DOM ANÓMALO INTERCALADO \--\>  
\<p class\="Texto-Cuerpo"\>  
  La teoría planetaria heliocéntrica propuesta en el siglo XVI enfrentó una dura censura eclesiástica
  \<span class\="nota-intercalada-ocr"\>1\. Copérnico decidió retrasar la publicación de su obra hasta el año de su muerte.\</span\>
  por contradecir directamente las interpretaciones geocéntricas de la época.  
\</p\>

Python  
\# IMPLEMENTACIÓN DE DETECCIÓN (PSEUDOCÓDIGO BEAUTIFULSOUP)  
\# Buscar elementos 'span' o 'div' internos dentro de párrafos principales  
\# que comiencen con una estructura de numeración de notas al pie.  
import re

patron\_num \= re.compile(r'^\\d+\[\\.\\s\\-\]+')  
for span in soup.find\_all(\['span', 'div'\], class\_=True):  
    \# Verificar si está dentro de un elemento de párrafo de texto regular  
    p\_padre \= span.find\_parent('p')  
    if p\_padre and patron\_num.match(span.get\_text().strip()):  
        \# Se identifica una nota intercalada.  
        \# Acción: Extraer el contenido para moverlo a la sección final  
        \# y reemplazar el nodo con una referencia normalizada.  
        pass

### **3.2. Texto plano no enlazado al final de capítulos**

* **Descripción del problema:** Ocurre habitualmente al guardar documentos procesados mediante reconocimiento óptico de caracteres (OCR) o herramientas como MS Word sin la correcta vinculación de referencias dinámicas53. El superíndice de la llamada se convierte en un texto plano convencional dentro del párrafo, y los cuerpos de las notas se acumulan linealmente al final del archivo en forma de párrafos ordinarios, perdiendo toda la lógica de enlaces hipervinculados bidireccionales53.  
* **Huella digital de detección:** Bloques de texto plano secuenciales situados al final de los archivos XHTML que inician con un patrón numérico encerrado entre corchetes, paréntesis o seguido de un punto (ej. \[1\], (1), 1.), sin presencia de elementos de anclaje a que apunten a llamadas correlativas en el cuerpo superior del archivo.

HTML  
\<\!-- EJEMPLO DE LLAMADA ANÓMALA PLANA \--\>  
\<p class\="Normal"\>La constante cuántica de Planck es un pilar de la física moderna. \[1\]\</p\>

\<\!-- CUERPO ANÓMALO PLANO AL CIERRE DEL DOCUMENTO \--\>  
\<p class\="Normal"\>\[1\] Max Planck propuso esta relación matemática fundamental en el año 1900\.\</p\>

Python  
\# IMPLEMENTACIÓN DE DETECCIÓN (PSEUDOCÓDIGO BEAUTIFULSOUP)  
\# Localizar párrafos que comiencen con patrones de notas al final del documento  
patron\_cuerpo \= re.compile(r'^\\\[(\\d+)\\\]\\s+(.\*)')  
cuerpos\_encontrados \= \[\]

for p in soup.find\_all('p'):  
    texto \= p.get\_text().strip()  
    match \= patron\_cuerpo.match(texto)  
    if match:  
        num\_nota \= match.group(1)  
        \# Buscar en el texto superior si existe un marcador de llamada aislado  
        \# para reconstruir el hipervínculo dinámico.  
        cuerpos\_encontrados.append((num\_nota, p))

### **3.3. Contenedores absolutos por OCR (Bloques flotantes desubicados)**

* **Descripción del problema:** Esta anomalía surge cuando la conversión de PDF a EPUB preserva las cajas de maquetación mediante el uso de estilos CSS con posicionamiento absoluto51. Los bloques que contienen las notas al pie físicas se declaran con coordenadas fijas en la pantalla, lo que destruye el carácter adaptativo (*reflowable*) del libro digital y provoca que el bloque de la nota se superponga visualmente al cuerpo principal de la lectura en dispositivos móviles51.  
* **Huella digital de detección:** Elementos contenedor div o p que poseen de manera directa en el código de marcado atributos style con propiedades CSS del tipo position:absolute o distanciados espaciales fijos medidos en píxeles (top:, left:, width:)51.

HTML  
\<\!-- EJEMPLO DE NOTA OCR CON POSICIONAMIENTO ABSOLUTO \--\>  
\<div style\="position:absolute; top:980px; left:40px; width:450px; font-size:10px;"\>  
  \<p\>1\. Stephen Hawking propuso la radiación de agujeros negros en su artículo de 1974\.\</p\>  
\</div\>

Python  
\# IMPLEMENTACIÓN DE DETECCIÓN (PSEUDOCÓDIGO BEAUTIFULSOUP)  
\# Buscar elementos con posicionamiento absoluto en línea  
for div in soup.find\_all(\['div', 'p'\], style=True):  
    style\_str \= div\['style'\]  
    if 'position' in style\_str and 'absolute' in style\_str:  
        \# Extraer los datos y limpiar los estilos absolutos  
        \# para reubicar la nota en la estructura fluida.  
        del div\['style'\]  
        \# Convertir a estructura de nota normalizada  
        pass

## **4\. Conclusiones y recomendaciones arquitectónicas para la normalización**

Para que el pipeline de conversión automatizado procese de manera exitosa los diferentes archivos XHTML procedentes de los doce motores analizados, el sistema en Python deberá apegarse de forma estricta a las siguientes directrices arquitectónicas:

1. **Aislamiento estructural mediante el patrón Strategy:** Se debe programar una clase base de estrategia que exponga métodos comunes de normalización. Cada motor o herramienta identificada en la sección primera poseerá su propia estrategia heredada (p. ej., InDesignFootnoteStrategy, VellumFootnoteStrategy, etc.), la cual se seleccionará dinámicamente mediante la inspección de los metadatos de creación del EPUB o firmas estructurales específicas encontradas en el archivo XHTML.  
2. **Abstracción de identificadores:** La estrategia debe identificar los anclajes de llamada y los cuerpos correspondientes utilizando los patrones abstractos detallados en la sección segunda, extraerlos de su ubicación original y reconstruir la relación de hipervínculo utilizando identificadores consecutivos unificados (por ejemplo, fn1, fnref1)27.  
3. **Consolidación de la sección final de notas:** Todos los cuerpos de notas normalizados deben agruparse al cierre de cada capítulo o sección dentro de un bloque semántico único compatible con el parser de Pandoc27:  
   HTML  
   \<section class\="footnotes" role\="doc-endnotes"\>  
     \<hr /\>  
     \<ol\>  
       \<\!-- Ítems de notas normalizados \--\>  
     \</ol\>  
   \</section\>

4. **Inyección de retroenlaces homogéneos:** Se debe eliminar todo caracter anómalo o vacío usado en los backlinks de origen (vacíos de InDesign, flechas de Calibre o retornos de Pressbooks) e inyectar un anclaje homogeneizado con la clase footnote-back y el caracter estándar Unicode de retorno de carro ↩27.

Siguiendo esta especificación de ingeniería, el desarrollador senior podrá construir un motor de normalización de BeautifulSoup altamente resistente y predecible, mitigando los problemas de visualización e indexación semántica en la transformación final hacia formatos de salida administrados por Pandoc27.

### **Obras citadas**

1. Best Book Formating Software: 2026 Comparison \- WifiTalents, [https://wifitalents.com/best/book-formating-software/](https://wifitalents.com/best/book-formating-software/)  
2. How to Format a Book With Vellum \- Author Media, [https://www.authormedia.com/how-to-format-a-book-with-vellum/](https://www.authormedia.com/how-to-format-a-book-with-vellum/)  
3. Best Book Formatting Software | 20 Tools Ranked (2026) \- Gitnux, [https://gitnux.org/best/book-formatting-software/](https://gitnux.org/best/book-formatting-software/)  
4. E-book conversion — calibre 9.9.0 documentation, [https://manual.calibre-ebook.com/conversion.html](https://manual.calibre-ebook.com/conversion.html)  
5. Making accessible ePubs with DAISY WordToEPUb plugin for Microsoft Word, [https://accessibledigitallearning.org/content/uploads/2021/09/Accessibility\_Toolkit\_ePub\_150921.pdf](https://accessibledigitallearning.org/content/uploads/2021/09/Accessibility_Toolkit_ePub_150921.pdf)  
6. How to Convert Word to EPUB Safely for Self-Publishers \- BookAutoAI, [https://blog.bookautoai.com/convert-word-to-epub/](https://blog.bookautoai.com/convert-word-to-epub/)  
7. Edit Content with the Visual and Code Editors \- Pressbooks User Guide, [https://guide.pressbooks.com/chapter/edit-content-with-the-visual-text-editors/](https://guide.pressbooks.com/chapter/edit-content-with-the-visual-text-editors/)  
8. Reedsy Studio: Plan, Draft, Edit, and Format your Book, [https://reedsy.com/studio](https://reedsy.com/studio)  
9. Export InDesign documents to an EPUB format \- Adobe Help Center, [https://helpx.adobe.com/ie/indesign/using/export-content-epub-cc.html](https://helpx.adobe.com/ie/indesign/using/export-content-epub-cc.html)  
10. Making ebooks with Sigil, HTML and CSS \- GitHub Pages, [http://electricbookworks.github.io/ebw-training/making-ebooks/text/1-html.html](http://electricbookworks.github.io/ebw-training/making-ebooks/text/1-html.html)  
11. Guide on converting a Google Docs text into an eBook \- Denys Poltorak \- Medium, [https://denyspoltorak.medium.com/guide-on-converting-a-google-docs-text-into-an-ebook-5b1abc65f69d](https://denyspoltorak.medium.com/guide-on-converting-a-google-docs-text-into-an-ebook-5b1abc65f69d)  
12. Chapter 5\. Importing Files \- Jutoh, [https://www.jutoh.com/bookv2/html/section-0009.html](https://www.jutoh.com/bookv2/html/section-0009.html)  
13. Jutoh Benefits and Features, [https://www.jutoh.com/features.html](https://www.jutoh.com/features.html)  
14. How to Format a Book for Print and Ebook in 2026 \- Authors Unite, [https://authorsunite.com/how-to-format-a-book](https://authorsunite.com/how-to-format-a-book)  
15. Footnotes \- Vellum Help, [https://help.vellum.pub/text-features/footnote/](https://help.vellum.pub/text-features/footnote/)  
16. Atticus Writing Software: The Complete 2026 Walkthrough for Coaches | Built\&Written, [https://www.builtwritten.com/blog/atticus-writing-software-2026](https://www.builtwritten.com/blog/atticus-writing-software-2026)  
17. How to Format a Book Professionally in 7 Simple Steps \- Reedsy, [https://reedsy.com/studio/resources/how-to-format-a-book](https://reedsy.com/studio/resources/how-to-format-a-book)  
18. How to Use Reedsy Book Editor \- Publish Drive, [https://publishdrive.com/convert-book-reedsy-book-editor.html](https://publishdrive.com/convert-book-reedsy-book-editor.html)  
19. Add Footnotes or Chapter Endnotes – Pressbooks User Guide \- OPEN OCO, [https://open.ocolearnok.org/userguide/chapter/add-footnotes-or-chapter-endnotes/](https://open.ocolearnok.org/userguide/chapter/add-footnotes-or-chapter-endnotes/)  
20. Use advanced book creation options in Pages \- Apple Support, [https://support.apple.com/en-us/108362](https://support.apple.com/en-us/108362)  
21. Kindle Create Tutorial \- Amazon KDP, [https://kdp.amazon.com/help/topic/GYVL2CASGU9ACFVU](https://kdp.amazon.com/help/topic/GYVL2CASGU9ACFVU)  
22. eBook Manuscript Formatting Guide \- Amazon KDP, [https://kdp.amazon.com/help?topicId=G200645680](https://kdp.amazon.com/help?topicId=G200645680)  
23. Kindle Formatting Guide: The Complete 2026 Guide to \- HMD Publishing, [https://hmdpublishing.com/blog/kindle-formatting-guide-guide](https://hmdpublishing.com/blog/kindle-formatting-guide-guide)  
24. WordToEPUB \- The DAISY Consortium, [https://daisy.org/activities/software/wordtoepub/](https://daisy.org/activities/software/wordtoepub/)  
25. Getting started with WordToEPUB \- The DAISY Consortium, [https://daisy.org/guidance/info-help/guidance-training/content-creation/getting-started-with-wordtoepub/](https://daisy.org/guidance/info-help/guidance-training/content-creation/getting-started-with-wordtoepub/)  
26. Pandoc User's Guide, [https://pandoc.org/MANUAL.html](https://pandoc.org/MANUAL.html)  
27. Differentiate between footnotes and endnotes · Issue \#4041 · jgm/pandoc \- GitHub, [https://github.com/jgm/pandoc/issues/4041](https://github.com/jgm/pandoc/issues/4041)  
28. Footnotes, Endnotes, Sidenotes and Popup Notes \- publisha.org, [https://www.publisha.org/pages/footnotes/](https://www.publisha.org/pages/footnotes/)  
29. InDesign Secrets Video: Creating Pop-Up Footnotes in Ebooks \- CreativePro Network, [https://creativepro.com/indesign-secrets-video-creating-pop-up-footnotes-ebooks/](https://creativepro.com/indesign-secrets-video-creating-pop-up-footnotes-ebooks/)  
30. Indesign epub export to kindle \- footnotes and hyperlink code conversion to Kindle Format, [https://community.adobe.com/questions-671/indesign-epub-export-to-kindle-footnotes-and-hyperlink-code-conversion-to-kindle-format-889158](https://community.adobe.com/questions-671/indesign-epub-export-to-kindle-footnotes-and-hyperlink-code-conversion-to-kindle-format-889158)  
31. Footnotes... what am I doing wrong? \- KDP Community, [https://www.kdpcommunity.com/s/question/0D5f400000FHzfbCAD/footnotes-what-am-i-doing-wrong?language=en\_US](https://www.kdpcommunity.com/s/question/0D5f400000FHzfbCAD/footnotes-what-am-i-doing-wrong?language=en_US)  
32. sigil-plugin-footnote-gen/plugin.py at master \- GitHub, [https://github.com/laggardkernel/sigil-plugin-footnote-gen/blob/master/plugin.py](https://github.com/laggardkernel/sigil-plugin-footnote-gen/blob/master/plugin.py)  
33. epub \- How can I put footnotes in an ebook?, [https://ebooks.stackexchange.com/questions/109/how-can-i-put-footnotes-in-an-ebook](https://ebooks.stackexchange.com/questions/109/how-can-i-put-footnotes-in-an-ebook)  
34. ePub \- MobileRead Wiki, [https://wiki.mobileread.com/wiki/EPub](https://wiki.mobileread.com/wiki/EPub)  
35. Inline Footnotes Question \- Scrivener for macOS \- Literature & Latte Forums, [https://forum.literatureandlatte.com/t/inline-footnotes-question/33725](https://forum.literatureandlatte.com/t/inline-footnotes-question/33725)  
36. How to handle footnotes when working with epub files \- Ebooks Stack Exchange, [https://ebooks.stackexchange.com/questions/6039/how-to-handle-footnotes-when-working-with-epub-files](https://ebooks.stackexchange.com/questions/6039/how-to-handle-footnotes-when-working-with-epub-files)  
37. Solved: create epub with footnotes \- Experts Exchange, [https://www.experts-exchange.com/questions/28009937/create-epub-with-footnotes.html](https://www.experts-exchange.com/questions/28009937/create-epub-with-footnotes.html)  
38. Looking to print/export a google doc with comments? Here you go. : r/googledocs \- Reddit, [https://www.reddit.com/r/googledocs/comments/1g5nrz5/looking\_to\_printexport\_a\_google\_doc\_with\_comments/](https://www.reddit.com/r/googledocs/comments/1g5nrz5/looking_to_printexport_a_google_doc_with_comments/)  
39. ePub Reader Setup \- Settings \- KPW Home Page, [https://kpwsite.com/home/content/eReader/setup.html](https://kpwsite.com/home/content/eReader/setup.html)  
40. Chapter 13: Working With Style Sheets \- Jutoh, [https://www.jutoh.com/bookv3/html/section-0017.html](https://www.jutoh.com/bookv3/html/section-0017.html)  
41. Vellum vs. Atticus for Non-Fiction Interior Book Design \- Jeremy B. Shapiro, [https://www.jeremyshapiro.com/2025/06/vellum-vs-atticus-for-non-fiction-interior-book-design/](https://www.jeremyshapiro.com/2025/06/vellum-vs-atticus-for-non-fiction-interior-book-design/)  
42. The epub:type Attribute \- Accessible Publishing Knowledge Base, [https://kb.daisy.org/publishing/docs/html/epub-type.html](https://kb.daisy.org/publishing/docs/html/epub-type.html)  
43. How to Format a Book Manuscript (+ Template) \- Reedsy, [https://reedsy.com/studio/resources/book-manuscript-format](https://reedsy.com/studio/resources/book-manuscript-format)  
44. EPUB 3 Creation and Fixing: The Complete Guide for Self-Published Authors (2026), [https://medium.com/@triomarketers/epub-3-creation-and-fixing-the-complete-guide-for-self-published-authors-2026-882f7e8fd91e](https://medium.com/@triomarketers/epub-3-creation-and-fixing-the-complete-guide-for-self-published-authors-2026-882f7e8fd91e)  
45. Use Shortcodes \- Pressbooks User Guide, [https://guide.pressbooks.com/chapter/use-shortcodes/](https://guide.pressbooks.com/chapter/use-shortcodes/)  
46. Automatic Pages and Export-only Content \- Pressbooks User Guide, [https://guide.pressbooks.com/chapter/automatic-pages/](https://guide.pressbooks.com/chapter/automatic-pages/)  
47. Appendix: Using Pressbooks – Publishing with VIVA, [https://viva.pressbooks.pub/vivapublishing/back-matter/appendix-pressbooks/](https://viva.pressbooks.pub/vivapublishing/back-matter/appendix-pressbooks/)  
48. EPUB Accessibility Updates in InDesign 2026 \- CreativePro Network, [https://creativepro.com/epub-accessibility-updates-in-indesign-2026/](https://creativepro.com/epub-accessibility-updates-in-indesign-2026/)  
49. EPUB Accessibility Techniques 1.2 \- W3C on GitHub, [https://w3c.github.io/epub-specs/epub34/a11y-tech/](https://w3c.github.io/epub-specs/epub34/a11y-tech/)  
50. EPUB (Electronic Publication) File Format Family \- The Library of Congress, [https://www.loc.gov/preservation/digital/formats/fdd/fdd000310.shtml](https://www.loc.gov/preservation/digital/formats/fdd/fdd000310.shtml)  
51. Basic HTML Formatting Guidelines \- Amazon KDP, [https://kdp.amazon.com/help?topicId=A1KSPVAI36UUC1](https://kdp.amazon.com/help?topicId=A1KSPVAI36UUC1)  
52. Embedding footnotes during compile in kindle and/or ebook format \- Scrivener for macOS, [https://forum.literatureandlatte.com/t/embedding-footnotes-during-compile-in-kindle-and-or-ebook-format/50765](https://forum.literatureandlatte.com/t/embedding-footnotes-during-compile-in-kindle-and-or-ebook-format/50765)  
53. The Complete Guide to Creating EPUB-Ready Documents for eBooks | by Paul Hoke, [https://medium.com/@paulhoke/the-complete-guide-to-creating-epub-ready-documents-for-ebooks-d166c0879939](https://medium.com/@paulhoke/the-complete-guide-to-creating-epub-ready-documents-for-ebooks-d166c0879939)  
54. 5\. Getting Content into Pressbooks, [https://opentextbooks.rug.nl/demobook/chapter/gettingcontentintopressbooks/](https://opentextbooks.rug.nl/demobook/chapter/gettingcontentintopressbooks/)  
55. Extension: footnotes \- Pandoc User's Guide, [https://www.uv.es/wiki/pandoc\_manual\_2.7.3.wiki?136](https://www.uv.es/wiki/pandoc_manual_2.7.3.wiki?136)
