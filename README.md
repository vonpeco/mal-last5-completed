# MAL Last 5 Completed

Genera **cinco imágenes PNG independientes** con las portadas de los cinco animes más recientemente actualizados dentro del estado **Completed** de la lista pública de MyAnimeList de `VonPeco`.

Cada portada tiene un enlace clickeable que abre la ficha correcta del anime en MAL. Las imágenes y los destinos se actualizan juntos cada seis horas.

## Cómo ponerlo en el perfil clásico

Después de que la acción termine correctamente, abrí:

`https://vonpeco.github.io/mal-last5-completed/profile-bbcode.txt`

Copiá el contenido completo y pegalo en el editor de tu perfil clásico de MAL. El bloque mantiene tres portadas en la primera fila y dos centradas debajo. Solo hay que pegarlo una vez: las URLs de imagen y los enlaces intermediarios son estables.

Cada imagen enlaza a una dirección propia de este sitio (`/go/1/` a `/go/5/`). Esas páginas se regeneran en cada actualización y redirigen al anime que ocupa actualmente esa posición en la lista. Así no quedan enlaces desactualizados cuando cambia el Top 5.

## Configuración inicial

1. En **Settings → Secrets and variables → Actions**, crear un repository secret llamado `MAL_CLIENT_ID` con el Client ID de la aplicación de MyAnimeList.
2. En **Settings → Pages**, seleccionar **Build and deployment → Source: GitHub Actions**.
3. La publicación se ejecuta al actualizar el código, manualmente desde **Actions**, y automáticamente cada seis horas.

El repositorio debe permanecer público para usar GitHub Pages gratis con GitHub Free. El Client ID queda almacenado como secreto de Actions y no se escribe en los archivos del repositorio.

## Orden de las entradas

La API se consulta con `status=completed` y `sort=list_updated_at`. Por eso el orden sigue la última actualización de cada entrada, que puede no coincidir exactamente con el día en que terminaste de ver el anime.

## Comprobación

- Página de vista previa: `https://vonpeco.github.io/mal-last5-completed/`
- BBCode listo para copiar: `https://vonpeco.github.io/mal-last5-completed/profile-bbcode.txt`
- Imagen individual: `https://vonpeco.github.io/mal-last5-completed/covers/anime-1.png`
- Destino dinámico de la primera portada: `https://vonpeco.github.io/mal-last5-completed/go/1/`

Si una acción falla, abrí **Actions** en GitHub y revisá el paso fallido. Confirmá que el secret se llame exactamente `MAL_CLIENT_ID` y que la lista de MAL siga siendo pública.
