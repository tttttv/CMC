FROM node:21

# set working directory
WORKDIR /app
COPY . .

# add `/app/node_modules/.bin` to $PATH
ENV PATH /app/node_modules/.bin:$PATH

# install app dependencies
RUN cat package.json
RUN npm install --include=dev --also=dev --loglevel verbose --production=false
RUN npm list -g --depth=4


# add app

# start app
CMD ["npm", "run", "dev"]