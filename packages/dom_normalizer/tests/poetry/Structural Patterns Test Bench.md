# Banco de Pruebas de Patrones Estructurales

- DOC_ID: StandardEbooks_Caso_Exacto

  - ```html
    <blockquote epub:type="z3998:poem">
      <p><span class="i1">Canta, oh musa...</span></p>
    </blockquote>
    ```

- DOC_ID: StandardEbooks_Caso_Estructural

  - ```html
    <blockquote epub:type="z3998:poem" class="clase-modificada">
      <p><span>Canta, oh musa...</span></p>
    </blockquote>
    ```

- DOC_ID: Library_Of_America_Caso_Exacto

  - ```html
    <table class="poem_table">
      <tr><td>Este es un verso de una tabla</td></tr>
    </table>
    ```

- DOC_ID: Library_Of_America_Caso_Estructural

  - ```html
    <table class="clase_corrupta_modificada">
      <tr><td>Este es un verso de una tabla</td></tr>
    </table>
    ```

- DOC_ID: EpubLibre_Caso_Exacto

  - ```html
    <div class="poema_custom">
      <div class="estrofa">
        <p class="verso">Canta, oh musa...</p>
      </div>
    </div>
    ```

- DOC_ID: EpubLibre_Caso_Estructural

  - ```html
    <div class="anonimo-sin-clase">
      <div>
        <p>Canta, oh musa...</p>
      </div>
    </div>
    ```

- DOC_ID: Penguin_Planeta_Caso_Exacto

  - ```html
    <div class="Layout-Poetry-Modern">
      <p class="verso">Silenciosa la noche avanza...</p>
    </div>
    ```

- DOC_ID: Penguin_Planeta_Caso_Estructural

  - ```html
    <div class="Layout-Modificado-No-Exacto">
      <p>Silenciosa la noche avanza...</p>
    </div>
    ```

- DOC_ID: Calibre_Auto_Caso_Exacto

  - ```html
    <p class="calibre_poetry_variant">
      Línea uno de calibre<br/>
      Línea dos de calibre<br/>
    </p>
    ```

- DOC_ID: Calibre_Auto_Caso_Estructural

  - ```html
    <p class="clase-borrada">
      Línea uno sin clase calibre<br/>
      Línea dos sin clase calibre<br/>
    </p>
    ```
