# Structural Patterns Transformation Output

## DOC_ID: StandardEbooks_Caso_Exacto

### Input
```html
<blockquote epub:type="z3998:poem">
      <p><span class="i1">Canta, oh musa...</span></p>
    </blockquote>
```

### HTML Output
```html
<body>
 <blockquote epub:type="z3998:poem">
  <div class="line-block">
   <span class="i1">
    Canta, oh musa...
   </span>
  </div>
 </blockquote>
</body>
```

### Markdown Output
```markdown
> | Canta, oh musa...
```

---

## DOC_ID: StandardEbooks_Caso_Estructural

### Input
```html
<blockquote epub:type="z3998:poem" class="clase-modificada">
      <p><span>Canta, oh musa...</span></p>
    </blockquote>
```

### HTML Output
```html
<body>
 <blockquote class="clase-modificada" epub:type="z3998:poem">
  <div class="line-block">
   <span>
    Canta, oh musa...
   </span>
  </div>
 </blockquote>
</body>
```

### Markdown Output
```markdown
> | Canta, oh musa...
```

---

## DOC_ID: Library_Of_America_Caso_Exacto

### Input
```html
<table class="poem_table">
      <tr><td>Este es un verso de una tabla</td></tr>
    </table>
```

### HTML Output
```html
<body>
 <div class="line-block">
  Este es un verso de una tabla
 </div>
</body>
```

### Markdown Output
```markdown
| Este es un verso de una tabla
```

---

## DOC_ID: Library_Of_America_Caso_Estructural

### Input
```html
<table class="clase_corrupta_modificada">
      <tr><td>Este es un verso de una tabla</td></tr>
    </table>
```

### HTML Output
```html
<body>
 <div class="line-block">
  Este es un verso de una tabla
 </div>
</body>
```

### Markdown Output
```markdown
| Este es un verso de una tabla
```

---

## DOC_ID: EpubLibre_Caso_Exacto

### Input
```html
<div class="poema_custom">
      <div class="estrofa">
        <p class="verso">Canta, oh musa...</p>
      </div>
    </div>
```

### HTML Output
```html
<body>
 <div class="line-block">
  Canta, oh musa...
 </div>
</body>
```

### Markdown Output
```markdown
| Canta, oh musa...
```

---

## DOC_ID: EpubLibre_Caso_Estructural

### Input
```html
<div class="anonimo-sin-clase">
      <div>
        <p>Canta, oh musa...</p>
      </div>
    </div>
```

### HTML Output
```html
<body>
 <div class="line-block">
  Canta, oh musa...
 </div>
</body>
```

### Markdown Output
```markdown
| Canta, oh musa...
```

---

## DOC_ID: Penguin_Planeta_Caso_Exacto

### Input
```html
<div class="Layout-Poetry-Modern">
      <p class="verso">Silenciosa la noche avanza...</p>
    </div>
```

### HTML Output
```html
<body>
 <div class="line-block">
  Silenciosa la noche avanza...
 </div>
</body>
```

### Markdown Output
```markdown
| Silenciosa la noche avanza...
```

---

## DOC_ID: Penguin_Planeta_Caso_Estructural

### Input
```html
<div class="Layout-Modificado-No-Exacto">
      <p>Silenciosa la noche avanza...</p>
    </div>
```

### HTML Output
```html
<body>
 <div class="line-block">
  Silenciosa la noche avanza...
 </div>
</body>
```

### Markdown Output
```markdown
| Silenciosa la noche avanza...
```

---

## DOC_ID: Calibre_Auto_Caso_Exacto

### Input
```html
<p class="calibre_poetry_variant">
      Línea uno de calibre<br/>
      Línea dos de calibre<br/>
    </p>
```

### HTML Output
```html
<body>
 <div class="line-block">
  Línea uno de calibre
  <br/>
  Línea dos de calibre
 </div>
</body>
```

### Markdown Output
```markdown
| Línea uno de calibre
| Línea dos de calibre
```

---

## DOC_ID: Calibre_Auto_Caso_Estructural

### Input
```html
<p class="clase-borrada">
      Línea uno sin clase calibre<br/>
      Línea dos sin clase calibre<br/>
    </p>
```

### HTML Output
```html
<body>
 <div class="line-block">
  Línea uno sin clase calibre
  <br/>
  Línea dos sin clase calibre
 </div>
</body>
```

### Markdown Output
```markdown
| Línea uno sin clase calibre
| Línea dos sin clase calibre
```

---

