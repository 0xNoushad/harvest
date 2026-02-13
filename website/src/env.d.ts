/// <reference types="astro/client" />
/// <reference path="../.astro/types.d.ts" />

declare module '*.png' {
  const value: ImageMetadata
  export default value
}

declare module '*.jpg' {
  const value: ImageMetadata
  export default value
}

declare module '*.jpeg' {
  const value: ImageMetadata
  export default value
}

declare module '*.webp' {
  const value: ImageMetadata
  export default value
}

declare module '*.svg' {
  const value: ImageMetadata
  export default value
}

interface ImageMetadata {
  src: string
  width: number
  height: number
  format: string
}
