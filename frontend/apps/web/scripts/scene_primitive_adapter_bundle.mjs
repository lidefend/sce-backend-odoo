import fs from 'node:fs';
import path from 'node:path';
import { build } from 'esbuild';
import { compileScript, parse } from 'vue/compiler-sfc';

const root = process.cwd();
const outfile = path.join(root, '.runtime/scene-primitive-adapter.mjs');
const metafile = path.join(root, '.runtime/scene-primitive-adapter.meta.json');

fs.mkdirSync(path.dirname(metafile), { recursive: true });
const result = await build({
  entryPoints: [`${root}/frontend/apps/web/src/components/design-system/scene-adapter/index.ts`],
  bundle: true,
  write: false,
  platform: 'browser',
  format: 'esm',
  outfile,
  metafile: true,
  define: {
    __VUE_OPTIONS_API__: 'true',
    __VUE_PROD_DEVTOOLS__: 'false',
    __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false',
    'process.env.NODE_ENV': '"production"',
  },
  resolveExtensions: ['.tsx', '.ts', '.jsx', '.js', '.css', '.json', '.mjs'],
  loader: { '.css': 'empty' },
  alias: {
    vue: `${root}/frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js`,
    'tdesign-vue-next': `${root}/frontend/packages/ui/node_modules/tdesign-vue-next`,
  },
  plugins: [{
    name: 'actual-vue-sfc',
    setup(builder) {
      builder.onLoad({ filter: /\.vue$/ }, (args) => {
        const { descriptor } = parse(fs.readFileSync(args.path, 'utf8'), { filename: args.path });
        return {
          contents: compileScript(descriptor, { id: args.path, inlineTemplate: true }).content,
          loader: 'ts',
          resolveDir: args.path.slice(0, args.path.lastIndexOf('/')),
        };
      });
    },
  }],
  logLevel: 'error',
});

fs.writeFileSync(metafile, JSON.stringify(result.metafile));
const payload = result.metafile;
const inputs = Object.keys(payload.inputs || {});
console.log(`[scene-primitive-adapter-bundle] PASS inputs=${inputs.length}`);
