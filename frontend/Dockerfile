FROM node:21-alpine

# set working directory
WORKDIR /app
COPY . .

# add `/app/node_modules/.bin` to $PATH
ENV PATH /app/node_modules/.bin:$PATH

# install app dependencies
RUN cat package.json
RUN npm install -g @hookform/resolvers @tanstack/react-query @tanstack/react-router axios form-data overlayscrollbars overlayscrollbars-react primereact react react-dom react-hook-form zod zustand @tanstack/router-devtools @tanstack/router-vite-plugin @trivago/prettier-plugin-sort-imports @types/node @types/react @types/react-dom @typescript-eslint/eslint-plugin @typescript-eslint/parser @vitejs/plugin-react-swc autoprefixer eslint eslint-plugin-react-hooks eslint-plugin-react-refresh postcss sass typescript vite


# add app

# start app
CMD ["npm", "run", "dev"]