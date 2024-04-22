FROM node:21-alpine

# set working directory
WORKDIR /app

# add `/app/node_modules/.bin` to $PATH
ENV PATH /app/node_modules/.bin:$PATH

# install app dependencies
COPY package.json .
RUN cat package.json
RUN npm i

# add app
COPY . .

# start app
CMD ["npm", "run", "build"]