FROM node:21-alpine

# set working directory
WORKDIR /app
COPY . .

# add `/app/node_modules/.bin` to $PATH
ENV PATH /app/node_modules/.bin:$PATH

# install app dependencies
RUN cat package.json
RUN npm i
RUN npm install typescript

# add app

# start app
CMD ["npm", "run", "build"]